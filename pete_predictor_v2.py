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

"""Callable responsible for running Inference on provided patches."""

import functools
from typing import Any, Mapping

from huggingface_hub import from_pretrained_keras
from ez_wsi_dicomweb import credential_factory
from ez_wsi_dicomweb import dicom_slide
from ez_wsi_dicomweb import patch_embedding
from ez_wsi_dicomweb import dicom_web_interface
from ez_wsi_dicomweb import patch_embedding_endpoints
from ez_wsi_dicomweb.ml_toolkit import dicom_path
import numpy as np
import tensorflow as tf

from data_models import embedding_response
from data_models import embedding_request
from data_models import embedding_converter
#from huggingface_hub import hf_hub_download
from huggingface_hub import snapshot_download



def _load_huggingface_model() -> tf.keras.Model:
  snapshot_download("google/path-foundation", local_dir="./model")
  return tf.keras.layers.TFSMLayer('./model', call_endpoint='serving_default') 
  #return from_pretrained_keras("./model", compile=False)


def _endpoint_model(ml_model: tf.keras.Model, image: np.ndarray) -> np.ndarray:
  """Function ez-wsi will use to run local ML model."""
  result = ml_model.signatures['serving_default'](
      tf.cast(tf.constant(image), tf.float32)
  )
  return result['output_0'].numpy()


# _ENDPOINT_MODEL = functools.partial(_endpoint_model, _load_huggingface_model())


class PetePredictor:
  """Callable responsible for generating embeddings."""

  def predict(
      self,
      prediction_input: Mapping[str, Any],
  ) -> Mapping[str, Any]:
    """Runs inference on provided patches.

    Args:
      prediction_input: JSON formatted input for embedding prediction.
      model: ModelRunner to handle model step.

    Returns:
      JSON formatted output.

    Raises:
      ERROR_LOADING_DICOM: If the provided patches are not concated.
    """
    embedding_json_converter = embedding_converter.EmbeddingConverterV2()
    request = embedding_json_converter.json_to_embedding_request(prediction_input)
    endpoint =  patch_embedding_endpoints.LocalEndpoint(_ENDPOINT_MODEL)

    embedding_results = []
    for instance in request.instances:
      patches = []
      if not isinstance(instance, embedding_request.DicomImageV2):
        raise ValueError('unsupported')
      token = instance.bearer_token
      if token:
        cf = credential_factory.TokenPassthroughCredentialFactory(token)
      else:
        cf = credential_factory.NoAuthCredentialsFactory()
      dwi = dicom_web_interface.DicomWebInterface(cf)
      path = dicom_path.FromString(instance.series_path)
      ds = dicom_slide.DicomSlide(dwi=dwi, path=path)
      level = ds.get_instance_level(instance.instance_uids[0])
      for coor in instance.patch_coordinates:
        patches.append(ds.get_patch(level, coor.x_origin, coor.y_origin, coor.width, coor.height))

      patch_embeddings = []
      for index, result in enumerate(patch_embedding.generate_patch_embeddings(endpoint, patches)):
        embedding = np.array(result.embedding)
        patch_embeddings.append(
            embedding_response.PatchEmbeddingV2(
                embedding_vector=embedding.tolist(),
                patch_coordinate=instance.patch_coordinates[index],
            ))
      embedding_results.append(
          embedding_response.embedding_instance_response_v2(patch_embeddings)
      )
    return embedding_converter.embedding_response_v2_to_json(embedding_results)
