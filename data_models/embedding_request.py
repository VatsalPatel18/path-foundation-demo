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

"""Request dataclasses for Pete."""

import dataclasses
import enum
from typing import Any, List, Mapping, Union
from data_models import patch_coordinate


class ModelSize(enum.Enum):
  UNDEFINED = 0
  SMALL = 1  # ~1M parameters
  MEDIUM = 2  # ~20M parameters.
  LARGE = 3  # ~100M parameters.


class ModelKind(enum.Enum):
  UNDEFINED = 0
  # Best suited for high magnification images.
  # Pixel spacings of .002mm, .001mm, .0005mm or 5x, 10x, 20x.
  LOW_PIXEL_SPACING = 1
  # Best suited for low magnification images.
  # Pixel spacings of .004mm, .008mm, .016mm, 5x_div_2, 5x_div4, 5x_div8.
  HIGH_PIXEL_SPACING = 2


@dataclasses.dataclass(frozen=True)
class EmbeddingInstanceV1:
  """An instance in a DICOM Embedding Request as described in the schema file."""

  dicom_web_store_url: str
  dicom_study_uid: str
  dicom_series_uid: str
  bearer_token: str
  ez_wsi_state: Union[str, Mapping[str, Any]]
  instance_uids: List[str]
  patch_coordinates: List[patch_coordinate.PatchCoordinate]


@dataclasses.dataclass(frozen=True)
class DicomImageV2:
  """An instance in a DICOM Embedding Request as described in the schema file."""
  series_path: str
  bearer_token: str
  extensions: Mapping[str, Any]
  instance_uids: List[str]
  patch_coordinates: List[patch_coordinate.PatchCoordinate]


@dataclasses.dataclass(frozen=True)
class GcsImageV2:
  """An instance in a DICOM Embedding Request as described in the schema file."""

  image_file_uri: str
  bearer_token: str
  extensions: Mapping[str, Any]
  patch_coordinates: List[patch_coordinate.PatchCoordinate]


@dataclasses.dataclass(frozen=True)
class EmbeddedImageV2:
  """An instance in a DICOM Embedding Request as described in the schema file."""
  image_bytes: str
  extensions: Mapping[str, Any]
  patch_coordinates: List[patch_coordinate.PatchCoordinate]


EmbeddingInstanceV2 = Union[DicomImageV2, GcsImageV2, EmbeddedImageV2]


@dataclasses.dataclass(frozen=True)
class EmbeddingParameters:
  """A prediction in a DICOM Embedding Request as described in the schema file."""

  model_size: str
  model_kind: str


@dataclasses.dataclass(frozen=True)
class EmbeddingRequestV1:
  """A DICOM Embedding Request is a single parameter and list of instances."""
  parameters: EmbeddingParameters
  instances: List[EmbeddingInstanceV1]


@dataclasses.dataclass(frozen=True)
class EmbeddingRequestV2:
  """A DICOM Embedding Request is a list of instances."""

  instances: List[EmbeddingInstanceV2]
