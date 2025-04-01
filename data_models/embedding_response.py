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

"""Response dataclasses for Pete."""

import dataclasses
import enum
from typing import Any, List, Mapping, Optional, Sequence

from ez_wsi_dicomweb import patch_embedding_endpoints

import pete_errors
from data_models import patch_coordinate

_MAX_ERROR_DESCRIPTION_LENGTH = 1024


class ErrorCode(enum.Enum):
  """The error codes for PeteErrorResponse mapped from PeteErrors."""

  TOO_MANY_PATCHES_ERROR = 'TOO_MANY_PATCHES_ERROR'
  INVALID_CREDENTIALS_ERROR = (
      patch_embedding_endpoints.EndpointJsonKeys.INVALID_CREDENTIALS
  )
  PATCH_DIMENSIONS_DO_NOT_MATCH_ENDPOINT_INPUT_DIMENSIONS_ERROR = (
      'PATCH_DIMENSIONS_DO_NOT_MATCH_ENDPOINT_INPUT_DIMENSIONS_ERROR'
  )
  INSTANCES_NOT_CONCATENATED_ERROR = 'INSTANCES_NOT_CONCATENATED_ERROR'
  INVALID_REQUEST_FIELD_ERROR = 'INVALID_REQUEST_FIELD_ERROR'
  INVALID_RESPONSE_ERROR = 'INVALID_RESPONSE_ERROR'
  LEVEL_NOT_FOUND_ERROR = 'LEVEL_NOT_FOUND_ERROR'
  EZ_WSI_STATE_ERROR = 'EZ_WSI_STATE_ERROR'
  IMAGE_ERROR = 'IMAGE_ERROR'
  HTTP_ERROR = 'HTTP_ERROR'
  INVALID_ICC_PROFILE_TRANSFORM_ERROR = 'INVALID_ICC_PROFILE_TRANSFORM_ERROR'
  IMAGE_DIMENSION_ERROR = 'IMAGE_DIMENSION_ERROR'
  DICOM_TILED_FULL_ERROR = 'DICOM_TILED_FULL_ERROR'
  DICOM_ERROR = 'DICOM_ERROR'
  DICOM_IMAGE_DOWNSAMPLING_TOO_LARGE_ERROR = (
      'DICOM_IMAGE_DOWNSAMPLING_TOO_LARGE_ERROR'
  )
  PATCH_OUTSIDE_OF_IMAGE_DIMENSIONS_ERROR = (
      'PATCH_OUTSIDE_OF_IMAGE_DIMENSIONS_ERROR'
  )
  DICOM_PATH_ERROR = 'DICOM_PATH_ERROR'
  GCS_IMAGE_PATH_FORMAT_ERROR = 'GCS_IMAGE_PATH_FORMAT_ERROR'
  UNAPPROVED_DICOM_STORE_ERROR = 'UNAPPROVED_DICOM_STORE_ERROR'
  UNAPPROVED_GCS_BUCKET_ERROR = 'UNAPPROVED_GCS_BUCKET_ERROR'


@dataclasses.dataclass(frozen=True)
class PeteErrorResponse:
  """The response when Pete is unable to successfully complete a request."""

  error_code: ErrorCode


@dataclasses.dataclass(frozen=True)
class PatchEmbeddingV1:
  """A List of embeddings, instance uids, and patch coordinate."""

  embeddings: List[float]
  patch_coordinate: patch_coordinate.PatchCoordinate


@dataclasses.dataclass(frozen=True)
class PatchEmbeddingV2:
  """A List of embeddings, instance uids, and patch coordinate."""

  embedding_vector: List[float]
  patch_coordinate: patch_coordinate.PatchCoordinate


@dataclasses.dataclass(frozen=True)
class EmbeddingResultV1:
  """The response when Pete is able to successfully complete a request."""

  dicom_study_uid: str
  dicom_series_uid: str
  instance_uids: List[str]
  patch_embeddings: List[PatchEmbeddingV1]


@dataclasses.dataclass(frozen=True)
class EmbeddingResponseV1:
  """An instance in a Embedding Response as described in the schema file."""

  model_version: str
  error_response: Optional[PeteErrorResponse]
  embedding_result: List[EmbeddingResultV1]

  def __post_init__(self):
    if self.error_response is None and self.embedding_result is None:
      raise pete_errors.InvalidResponseError(
          'At least one of error_response or embedding_result must be set.'
      )


def embedding_instance_response_v2(
    results: Sequence[PatchEmbeddingV2],
) -> Mapping[str, Any]:
  """Returns a JSON-serializable embedding instance responses."""
  return {
      patch_embedding_endpoints.EndpointJsonKeys.RESULT: {
          patch_embedding_endpoints.EndpointJsonKeys.PATCH_EMBEDDINGS: [
              dataclasses.asdict(patch_embedding) for patch_embedding in results
          ]
      },
  }


def instance_error_response_v2(
    error_code: ErrorCode, description: str = ''
) -> Mapping[str, Any]:
  error = {
      patch_embedding_endpoints.EndpointJsonKeys.ERROR_CODE: error_code.value
  }
  if description:
    error[patch_embedding_endpoints.EndpointJsonKeys.ERROR_CODE_DESCRIPTION] = (
        description[:_MAX_ERROR_DESCRIPTION_LENGTH]
    )
  return {
      patch_embedding_endpoints.EndpointJsonKeys.ERROR: error,
  }


def prediction_error_response_v2(error_code: ErrorCode) -> Mapping[str, Any]:
  return {
      patch_embedding_endpoints.EndpointJsonKeys.VERTEXAI_ERROR: (
          error_code.value
      )
  }
