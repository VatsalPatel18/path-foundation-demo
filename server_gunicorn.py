# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gunicorn application for passing requests through to the executor command.

Provides a thin, subject-agnostic request server for Vertex endpoints which
handles requests by piping their JSON bodies to the given executor command
and returning the json output.
"""

from collections.abc import Mapping
import http
import os
import sys
from typing import Any, Optional, Sequence
import json
from flask_cors import CORS
import diskcache
import gzip
from io import BytesIO
import shutil
import tempfile


import requests

from absl import app
from absl import logging
import auth
import flask
from flask import render_template, send_from_directory, Response, send_file, request, current_app, abort
from gunicorn.app import base as gunicorn_base
from flask_caching import Cache

# import pete_predictor_v2

# Define a persistent cache directory
CACHE_DIR = "/home/user/app/path-cache"

# Configure the cache to use the persistent directory
cache_disk = diskcache.Cache(CACHE_DIR, size_limit=45e9)  # Limit cache to 45GB

print(f"Cache stats: {cache_disk.stats()}")


DICOM_SERVER_URL = os.environ.get("DICOM_SERVER_URL")
PREDICT_SERVER_URL = os.environ.get("PREDICT_ENDPOINT_URL")


def validate_allowed_predict_request(data):
    for item in data['instances']:
        if 'dicom_path' not in item:
            raise ValueError("Missing 'dicom_path' key in request data.")
        if 'patch_coordinates' not in item:
            raise ValueError("Missing 'patch_coordinates' key in request data.")
        if 'raw_image_bytes' in item:
            raise ValueError("'raw_image_bytes' key found in request data, but it is not expected")
        if 'image_file_uri' in item:
            raise ValueError("'image_file_uri' key found in request data, but it is not expected")


def test_series_path_prefix(data, server_url):
    for item in data['instances']:
        series_path = item['dicom_path']['series_path']
        if not series_path.startswith(server_url):
            logging.error(f"series_path '{series_path}' does not start with '{server_url}'")
            return False
    return True


def replace_series_path_prefix(data, prefix, server_url):
    for item in data['instances']:
        item['dicom_path']['series_path'] = item['dicom_path']['series_path'].replace(prefix, server_url)
    return data


def provide_dicom_server_token(data, token):
    for item in data['instances']:
        item['bearer_token'] = token
    return data


def compress_response(json_data):
    """Compresses JSON data using gzip."""
    compressed_data = BytesIO()
    with gzip.GzipFile(fileobj=compressed_data, mode='w') as gz:
        gz.write(json_data.encode('utf-8'))
    return compressed_data.getvalue()


def create_gzipped_response(data, status=http.HTTPStatus.OK.value, content_type='application/json'):
    """Creates a gzipped Flask response."""
    json_data = json.dumps(data)
    compressed_data = compress_response(json_data)
    response = Response(compressed_data, status=status, content_type=content_type)
    response.headers['Content-Encoding'] = 'gzip'
    return response


def get_cached_and_uncached_patches(instance, dicom_path):
    """Separates cached and uncached patches."""
    cached_patch_embeddings = []
    uncached_patches = []
    uncached_patch_indices = []
    for i, patch in enumerate(instance['patch_coordinates']):
        cache_key = json.dumps({"dicom_path": dicom_path, "patch": patch}, sort_keys=True)
        cached_result = cache_disk.get(cache_key)
        if cached_result is not None:
            cached_patch_embeddings.append({"patch_coordinate": patch, "embedding_vector": cached_result})
        else:
            uncached_patches.append(patch)
            uncached_patch_indices.append(i)
    return cached_patch_embeddings, uncached_patches, uncached_patch_indices


def process_new_results(response_json, dicom_path):
    """Processes new results from the prediction server."""
    new_patch_embeddings = []
    if "predictions" in response_json:
        for prediction in response_json["predictions"]:
            if "result" in prediction and "patch_embeddings" in prediction["result"]:
                for patch_embedding in prediction["result"]["patch_embeddings"]:
                    patch = patch_embedding["patch_coordinate"]
                    embedding_vector = patch_embedding["embedding_vector"]
                    cache_key = json.dumps({"dicom_path": dicom_path, "patch": patch}, sort_keys=True)
                    cache_disk.set(cache_key, embedding_vector)
                    new_patch_embeddings.append({"patch_coordinate": patch, "embedding_vector": embedding_vector})
            else:
                logging.error("Unexpected response format: missing 'result' or 'patch_embeddings'")
                return None
    else:
        logging.error("Unexpected response format: missing 'predictions'")
        return None
    return new_patch_embeddings


def combine_results(instance, cached_patch_embeddings, new_patch_embeddings, uncached_patch_indices):
    """Combines cached and new results."""
    final_patch_embeddings = [None] * len(instance['patch_coordinates'])
    cached_index = 0
    new_index = 0
    for i in range(len(instance['patch_coordinates'])):
        if i in uncached_patch_indices:
            final_patch_embeddings[i] = new_patch_embeddings[new_index]
            new_index += 1
        else:
            final_patch_embeddings[i] = cached_patch_embeddings[cached_index]
            cached_index += 1
    return final_patch_embeddings


def _create_app() -> flask.Flask:
    """Creates a Flask app with the given executor."""
    # Create credentials and get access token on startup
    try:
        global credentials
        credentials = auth.create_credentials()
        auth.refresh_credentials(credentials)

    except ValueError as e:
        logging.exception(f"Failed to create credentials: {e}")
        # Handle credential creation failure appropriately, e.g., exit the application.
        sys.exit(1)
    # predictor = pete_predictor_v2.PetePredictor()
    flask_app = flask.Flask(__name__, static_folder='web', static_url_path='')
    CORS(flask_app, origins='http://localhost:5432')
    flask_app.config.from_mapping({"CACHE_TYPE": "simple"})
    cache = Cache(flask_app)

    @flask_app.route("/", methods=["GET"])
    def display_html():
        index_path = 'web/index.html'
        try:
            with open(index_path, 'r') as f:
                content = f.read()
                return Response(content, mimetype='text/html')
        except FileNotFoundError:
            abort(404, f"Error: index.html not found at {index_path}")

    @flask_app.route("/dicom/<path:url_path>", methods=["GET"])
    @cache.cached(timeout=0)
    def dicom(url_path):
        access_token = auth.get_access_token_refresh_if_needed(credentials)

        if not DICOM_SERVER_URL:
            abort(http.HTTPStatus.INTERNAL_SERVER_ERROR.value, "DICOM server URL not configured.")

        full_url = f"{DICOM_SERVER_URL}/{url_path}"
        headers = dict()  # flask.request.headers
        headers['Authorization'] = f"Bearer {access_token}"

        try:
            response = requests.get(full_url, params=flask.request.args, data=flask.request.get_data(), headers=headers)
            response.raise_for_status()
            return Response(response.content, status=response.status_code, content_type=response.headers['Content-Type'])
        except requests.RequestException as e:
            logging.exception("Error proxying request to DICOM server. %s", e)
            headers['Authorization'] = "hidden"
            censored_content = response.content.replace("Bearer " + access_token, "hidden")
            logging.error("Interal request headers: %s", json.dumps(headers, indent=2))
            logging.error("Internal request data: %s", censored_content)
            abort(http.HTTPStatus.BAD_GATEWAY.value, f"Error proxying request to DICOM server: {e}")

    @flask_app.route("/predict", methods=["POST"])
    def predict():
        access_token = auth.get_access_token_refresh_if_needed(credentials)

        if not PREDICT_SERVER_URL:
            abort(http.HTTPStatus.INTERNAL_SERVER_ERROR.value, "PREDICT server URL not configured.")

        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
        }

        try:
            body = json.loads(flask.request.get_data())
            validate_allowed_predict_request(body)
        except ValueError as e:
            abort(http.HTTPStatus.BAD_REQUEST.value, f"disallowed {str(e)}")

        try:
            body = replace_series_path_prefix(body, "http://localhost:8080/dicom/", "/dicom/")
            if not test_series_path_prefix(body, '/dicom/'):
                abort(http.HTTPStatus.BAD_REQUEST.value, "series_path does not start with dicom server url.")

            body = replace_series_path_prefix(body, "/dicom/", f"{DICOM_SERVER_URL}/")

            instance = body['instances'][0]  # assume single instance
            dicom_path = instance['dicom_path']

            cached_patch_embeddings, uncached_patches, uncached_patch_indices = get_cached_and_uncached_patches(instance, dicom_path)

            # If all patches are cached, return the cached results
            if not uncached_patches:
                return create_gzipped_response({"predictions": [{"result": {"patch_embeddings": cached_patch_embeddings}} ]})

            # Prepare the request for uncached patches
            request_body = {"instances": [{"dicom_path": dicom_path, "patch_coordinates": uncached_patches}]}
            request_body = provide_dicom_server_token(request_body, access_token)

            response = requests.post(PREDICT_SERVER_URL, json=request_body, headers=headers)
            response.raise_for_status()

            response_json = response.json()

            new_patch_embeddings = process_new_results(response_json, dicom_path)
            if new_patch_embeddings is None:
                abort(http.HTTPStatus.INTERNAL_SERVER_ERROR, "Unexpected response format from predict server")

            final_patch_embeddings = combine_results(instance, cached_patch_embeddings, new_patch_embeddings, uncached_patch_indices)

            return create_gzipped_response({"predictions": [{"result": {"patch_embeddings": final_patch_embeddings}} ]}, status=response.status_code)

        except requests.RequestException as e:
            headers['Authorization'] = "hidden"
            censored_content = request_body.content.replace("Bearer " + access_token, "hidden")            
            logging.exception("Error proxying request to predict server: %s", e)
            print("Internal request headers:", json.dumps(headers, indent=2))
            print("Internal request body:", json.dumps(censored_content, indent=2))
            abort(http.HTTPStatus.BAD_GATEWAY.value, "Error proxying request to predict server.")
        except json.JSONDecodeError as e:
            headers['Authorization'] = "hidden"
            censored_content = request_body.content.replace("Bearer " + access_token, "hidden")
            logging.exception("Error decoding JSON response from predict server: %s", e)
            print("Internal request headers:", json.dumps(headers, indent=2))
            print("Internal request body:", json.dumps(censored_content, indent=2))
            abort(http.HTTPStatus.BAD_GATEWAY.value, "Error decoding JSON response from predict server.")

    @flask_app.route("/download_cache", methods=["GET"])
    def download_cache():
        """
        Downloads the entire cache directory as a zip file.
        """
        print("Downloading cache")
        print(f"Cache stats: {cache_disk.stats()}")
        zip_filename = "path-cache.zip"
        # Use tempfile to create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_filepath = os.path.join(temp_dir, zip_filename)

            try:
                shutil.make_archive(
                    os.path.splitext(zip_filepath)[0],
                    "zip",
                    CACHE_DIR,
                )

                # Send the file and delete it afterwards
                return send_file(
                    zip_filepath,
                    mimetype="application/zip",
                    as_attachment=True,
                    download_name=zip_filename,
                )
            except Exception as e:
                current_app.logger.error(f"Error creating zip archive: {e}")
                abort(500, f"Error creating zip archive: {e}")

    return flask_app


class PredictionApplication(gunicorn_base.BaseApplication):
    """Application to serve predictors on Vertex endpoints using gunicorn."""

    def __init__(
            self,
            *,
            options: Optional[Mapping[str, Any]] = None,
    ):
        self.options = options or {}
        self.options = dict(self.options)
        self.options["preload_app"] = False
        self.application = _create_app()
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self) -> flask.Flask:
        return self.application


def main(argv: Sequence[str]) -> None:
    options = {'bind': f'0.0.0.0:8080',
               'workers': 6,
               'timeout': 600
               }
    PredictionApplication(options=options).run()


if __name__ == '__main__':
    app.run(main)
