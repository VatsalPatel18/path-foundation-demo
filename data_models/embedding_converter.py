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

"""Converts Embedding Requests and Responses to json and vice versa."""

import dataclasses
import json
from typing import Any, List, Mapping, Sequence

from ez_wsi_dicomweb import patch_embedding_endpoints

import pete_errors
from data_models import embedding_request
from data_models import embedding_response
from data_models import patch_coordinate as patch_coordinate_module

_EndpointJsonKeys = patch_embedding_endpoints.EndpointJsonKeys


class ValidationError(Exception):
  pass


class _InvalidCoordinateError(Exception):
  pass


class _InstanceUIDMetadataError(Exception):
  pass


def validate_int(val: Any) -> int:
  if isinstance(val, float):
    cast_val = int(val)
    if cast_val != val:
      raise ValidationError('coordinate value is not int')
    val = cast_val
  elif not isinstance(val, int):
    raise ValidationError('coordinate value is not int')
  return val


def _get_patch_coord(patch_coordinates: Sequence[Mapping[str, Any]]):
  """Returns patch coodianates."""
  result = []
  if not isinstance(patch_coordinates, list):
    raise _InvalidCoordinateError('patch_coordinates is not list')
  for patch_coordinate in patch_coordinates:
    try:
      pc = patch_coordinate_module.create_patch_coordinate(**patch_coordinate)
    except TypeError as exp:
      if not isinstance(patch_coordinate, dict):
        raise _InvalidCoordinateError('Patch coordinate is not dict.') from exp
      keys = ', '.join(
          list(
              dataclasses.asdict(
                  patch_coordinate_module.create_patch_coordinate(0, 0)
              )
          )
      )
      raise _InvalidCoordinateError(
          f'Patch coordinate dict has invalid keys; expecting: {keys}'
      ) from exp
    try:
      validate_int(pc.x_origin)
      validate_int(pc.y_origin)
      validate_int(pc.width)
      validate_int(pc.height)
    except ValidationError as exp:
      raise _InvalidCoordinateError(
          f'Invalid patch coordinate; x_origin: {pc.x_origin}, y_origin:'
          f' {pc.y_origin}, width: {pc.width}, height: {pc.height}'
      ) from exp
    result.append(pc)
  if not result:
    raise _InvalidCoordinateError('empty patch_coordinates')
  return result


def embedding_response_v1_to_json(
    response: embedding_response.EmbeddingResponseV1,
) -> Mapping[str, Any]:
  """Loads the model artifact.

  Args:
    response: Structed EmbeddingResponse object.

  Returns:
    The value of the JSON payload to return in the API.
  """
  json_response = dataclasses.asdict(response)
  if response.error_response:
    json_response['error_response'][
        'error_code'
    ] = response.error_response.error_code.value
  return {_EndpointJsonKeys.PREDICTIONS: json_response}


def embedding_response_v2_to_json(
    json_response: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
  return {_EndpointJsonKeys.PREDICTIONS: json_response}


def validate_str_list(val: Any) -> List[str]:
  if not isinstance(val, List):
    raise ValidationError('not list')
  for v in val:
    if not isinstance(v, str) or not v:
      raise ValidationError('list contains invalid value')
  return val


def _validate_instance_uids_not_empty_str_list(val: Any) -> List[str]:
  try:
    val = validate_str_list(val)
  except ValidationError as exp:
    raise _InstanceUIDMetadataError() from exp
  if not val:
    raise _InstanceUIDMetadataError('list is empty')
  return val


def validate_str_key_dict(val: Any) -> Mapping[str, Any]:
  if not isinstance(val, dict):
    raise ValidationError('not a dict')
  if val:
    for k in val:
      if not isinstance(k, str) or not k:
        raise ValidationError('dict contains invalid value')
  return val


def validate_str(val: Any) -> str:
  if not isinstance(val, str):
    raise ValidationError('not string')
  return val


def _validate_not_empty_str(val: Any) -> str:
  if not isinstance(val, str) or not val:
    raise ValidationError('not string or empty')
  return val


def _generate_instance_metadata_error_string(
    metadata: Mapping[str, Any], *keys: str
) -> str:
  """returns instance metadata as a error string."""
  result = {}
  for key in keys:
    if key not in metadata:
      continue
    if key == _EndpointJsonKeys.EXTENSIONS:
      value = metadata[key]
      if isinstance(value, Mapping):
        value = dict(value)
        # Strip ez_wsi_state from output.
        # Not contributing to validation errors here and may be very large.
        if _EndpointJsonKeys.EZ_WSI_STATE in value:
          del value[_EndpointJsonKeys.EZ_WSI_STATE]
          result[key] = value
          continue
    elif key == _EndpointJsonKeys.BEARER_TOKEN:
      value = metadata[key]
      # If bearer token is present, and defined strip
      if isinstance(value, str) and value:
        result[key] = 'PRESENT'
        continue
    # otherwise just associate key and value.
    result[key] = metadata[key]
  return json.dumps(result, sort_keys=True)


def _validate_instance_list(json_metadata: Mapping[str, Any]) -> List[Any]:
  val = json_metadata.get(_EndpointJsonKeys.INSTANCES)
  if isinstance(val, list):
    return val
  raise pete_errors.InvalidRequestFieldError(
      'Invalid input, missing expected'
      f' key: {_EndpointJsonKeys.INSTANCES} and associated list of values.'
  )


class EmbeddingConverterV1:
  """Class containing methods for transforming embedding request and responses."""

  def json_to_embedding_request(
      self, json_metadata: Mapping[str, Any]
  ) -> embedding_request.EmbeddingRequestV1:
    """Converts json to embedding request.

    Args:
      json_metadata: The value of the JSON payload provided to the API.

    Returns:
      Structured EmbeddingRequest object.

    Raises:
      InvalidRequestFieldError: If the provided fields are invalid.
    """
    instances = []
    try:
      model_params = json_metadata[_EndpointJsonKeys.PARAMETERS]
      try:
        parameters = embedding_request.EmbeddingParameters(
            model_size=_validate_not_empty_str(
                model_params.get(_EndpointJsonKeys.MODEL_SIZE)
            ),
            model_kind=_validate_not_empty_str(
                model_params.get(_EndpointJsonKeys.MODEL_KIND)
            ),
        )
      except ValidationError as exp:
        raise pete_errors.InvalidRequestFieldError(
            'Invalid model size and/or kind parameters.'
        ) from exp
      for instance in _validate_instance_list(json_metadata):
        ez_wsi_state = instance.get(_EndpointJsonKeys.EZ_WSI_STATE, {})
        try:
          ez_wsi_state = validate_str_key_dict(ez_wsi_state)
        except ValidationError:
          try:
            ez_wsi_state = validate_str(ez_wsi_state)
          except ValidationError as exp:
            raise pete_errors.InvalidRequestFieldError(
                'Invalid EZ-WSI state metadata.'
            ) from exp
        try:
          instances.append(
              embedding_request.EmbeddingInstanceV1(
                  dicom_web_store_url=_validate_not_empty_str(
                      instance.get(_EndpointJsonKeys.DICOM_WEB_STORE_URL)
                  ),
                  dicom_study_uid=_validate_not_empty_str(
                      instance.get(_EndpointJsonKeys.DICOM_STUDY_UID)
                  ),
                  dicom_series_uid=_validate_not_empty_str(
                      instance.get(_EndpointJsonKeys.DICOM_SERIES_UID)
                  ),
                  bearer_token=_validate_not_empty_str(
                      instance.get(_EndpointJsonKeys.BEARER_TOKEN)
                  ),
                  ez_wsi_state=ez_wsi_state,
                  instance_uids=_validate_instance_uids_not_empty_str_list(
                      instance.get(_EndpointJsonKeys.INSTANCE_UIDS)
                  ),
                  patch_coordinates=_get_patch_coord(
                      instance.get(_EndpointJsonKeys.PATCH_COORDINATES)
                  ),
              )
          )
        except ValidationError as exp:
          instance_error_msg = _generate_instance_metadata_error_string(
              instance,
              _EndpointJsonKeys.DICOM_WEB_STORE_URL,
              _EndpointJsonKeys.DICOM_STUDY_UID,
              _EndpointJsonKeys.DICOM_SERIES_UID,
              _EndpointJsonKeys.BEARER_TOKEN,
              _EndpointJsonKeys.INSTANCE_UIDS,
          )
          raise pete_errors.InvalidRequestFieldError(
              f'Invalid instance; {instance_error_msg}'
          ) from exp
        except _InstanceUIDMetadataError as exp:
          instance_error_msg = _generate_instance_metadata_error_string(
              instance,
              _EndpointJsonKeys.PATCH_COORDINATES,
          )
          raise pete_errors.InvalidRequestFieldError(
              f'Invalid DICOM SOP Instance UID metadata; {instance_error_msg}'
          ) from exp
    except _InvalidCoordinateError as exp:
      raise pete_errors.InvalidRequestFieldError(
          f'Invalid patch coordinate; {exp}'
      ) from exp
    except (TypeError, ValueError, KeyError) as exp:
      raise pete_errors.InvalidRequestFieldError(
          f'Invalid input: {json.dumps(json_metadata)}'
      ) from exp
    return embedding_request.EmbeddingRequestV1(
        parameters=parameters, instances=instances
    )


class EmbeddingConverterV2:
  """Class containing methods for transforming embedding request and responses."""

  def json_to_embedding_request(
      self, json_metadata: Mapping[str, Any]
  ) -> embedding_request.EmbeddingRequestV2:
    """Converts json to embedding request.

    Args:
      json_metadata: The value of the JSON payload provided to the API.

    Returns:
      Structured EmbeddingRequest object.

    Raises:
      InvalidRequestFieldError: If the provided fields are invalid.
    """
    instances = []
    for instance in _validate_instance_list(json_metadata):
      try:
        patch_coordinates = _get_patch_coord(
            instance.get(_EndpointJsonKeys.PATCH_COORDINATES)
        )
      except _InvalidCoordinateError as exp:
        instance_error_msg = _generate_instance_metadata_error_string(
            instance,
            _EndpointJsonKeys.PATCH_COORDINATES,
        )
        raise pete_errors.InvalidRequestFieldError(
            f'Invalid patch coordinate; {exp}; {instance_error_msg}'
        ) from exp
      if _EndpointJsonKeys.DICOM_PATH in instance:
        try:
          dicom_path = validate_str_key_dict(
              instance.get(_EndpointJsonKeys.DICOM_PATH)
          )
        except ValidationError as exp:
          raise pete_errors.InvalidRequestFieldError(
              'Invalid DICOM path.'
          ) from exp
        try:
          instances.append(
              embedding_request.DicomImageV2(
                  series_path=_validate_not_empty_str(
                      dicom_path.get(_EndpointJsonKeys.SERIES_PATH)
                  ),
                  bearer_token=validate_str(
                      instance.get(
                          _EndpointJsonKeys.BEARER_TOKEN,
                          '',
                      )
                  ),
                  extensions=validate_str_key_dict(
                      instance.get(
                          _EndpointJsonKeys.EXTENSIONS,
                          {},
                      )
                  ),
                  instance_uids=_validate_instance_uids_not_empty_str_list(
                      dicom_path.get(_EndpointJsonKeys.INSTANCE_UIDS)
                  ),
                  patch_coordinates=patch_coordinates,
              )
          )
        except _InstanceUIDMetadataError as exp:
          error_msg = _generate_instance_metadata_error_string(
              instance,
              _EndpointJsonKeys.SERIES_PATH,
              _EndpointJsonKeys.BEARER_TOKEN,
              _EndpointJsonKeys.EXTENSIONS,
              _EndpointJsonKeys.INSTANCE_UIDS,
          )
          raise pete_errors.InvalidRequestFieldError(
              f'Invalid DICOM SOP Instance UID metadata; {error_msg}'
          ) from exp
        except ValidationError as exp:
          error_msg = _generate_instance_metadata_error_string(
              instance,
              _EndpointJsonKeys.SERIES_PATH,
              _EndpointJsonKeys.BEARER_TOKEN,
              _EndpointJsonKeys.EXTENSIONS,
              _EndpointJsonKeys.INSTANCE_UIDS,
          )
          raise pete_errors.InvalidRequestFieldError(
              f'DICOM instance JSON formatting is invalid; {error_msg}'
          ) from exp
      elif _EndpointJsonKeys.IMAGE_FILE_URI in instance:
        try:
          instances.append(
              embedding_request.GcsImageV2(
                  image_file_uri=_validate_not_empty_str(
                      instance.get(_EndpointJsonKeys.IMAGE_FILE_URI)
                  ),
                  bearer_token=validate_str(
                      instance.get(
                          _EndpointJsonKeys.BEARER_TOKEN,
                          '',
                      )
                  ),
                  extensions=validate_str_key_dict(
                      instance.get(
                          _EndpointJsonKeys.EXTENSIONS,
                          {},
                      )
                  ),
                  patch_coordinates=patch_coordinates,
              )
          )
        except ValidationError as exp:
          error_msg = _generate_instance_metadata_error_string(
              instance,
              _EndpointJsonKeys.IMAGE_FILE_URI,
              _EndpointJsonKeys.BEARER_TOKEN,
              _EndpointJsonKeys.EXTENSIONS,
          )
          raise pete_errors.InvalidRequestFieldError(
              'Google Cloud Storage instance JSON formatting is invalid;'
              f' {error_msg}'
          ) from exp
      elif _EndpointJsonKeys.RAW_IMAGE_BYTES in instance:
        try:
          instances.append(
              embedding_request.EmbeddedImageV2(
                  image_bytes=_validate_not_empty_str(
                      instance.get(_EndpointJsonKeys.RAW_IMAGE_BYTES)
                  ),
                  extensions=validate_str_key_dict(
                      instance.get(
                          _EndpointJsonKeys.EXTENSIONS,
                          {},
                      )
                  ),
                  patch_coordinates=patch_coordinates,
              )
          )
        except ValidationError as exp:
          error_msg = _generate_instance_metadata_error_string(
              instance,
              _EndpointJsonKeys.IMAGE_FILE_URI,
              _EndpointJsonKeys.BEARER_TOKEN,
              _EndpointJsonKeys.EXTENSIONS,
          )
          raise pete_errors.InvalidRequestFieldError(
              'Embedded image instance JSON formatting is invalid; '
              f' {error_msg}'
          ) from exp
      else:
        raise pete_errors.InvalidRequestFieldError('unidentified type')
    return embedding_request.EmbeddingRequestV2(instances)
