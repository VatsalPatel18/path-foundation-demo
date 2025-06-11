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

"""Error classes for Pete."""


class InternalBugError(Exception):
  """Internal error capture exceptions which should never happen.

  The exception is purposefully not a child of PeteError to prevent it from
  being caught by pete exception handling logic. If InternalBugError are
  raised they should be investigated as bugs. Most internal errors check for
  expected conditions between the EZ-WSI pete interface.
  """


class PeteError(Exception):
  """Base error class for Pete Errors."""

  def __init__(self, message: str = '', api_description: str = ''):
    """Errors with optional alternative descriptions for API echoing."""
    super().__init__(message if message else api_description)
    self._api_description = api_description

  @property
  def api_description(self) -> str:
    """Returns the API description of the error."""
    return self._api_description if self._api_description else str(self)


class InstancesNotConcatenatedError(PeteError):
  pass


class InvalidRequestFieldError(PeteError):
  pass


class InvalidResponseError(PeteError):
  pass


class InvalidCredentialsError(PeteError):
  pass


class LevelNotFoundError(PeteError):
  pass


class TooManyPatchesError(PeteError):
  pass


class EzWsiStateError(PeteError):
  pass


class GcsImagePathFormatError(PeteError):
  pass


class ImageError(PeteError):
  pass


class PatchOutsideOfImageDimensionsError(PeteError):
  pass


class HttpError(PeteError):
  pass


class InvalidIccProfileTransformError(PeteError):
  pass


class ImageDimensionError(PeteError):
  pass


class DicomTiledFullError(PeteError):
  pass


class DicomPathError(PeteError):
  pass


class DicomError(PeteError):
  pass


class DicomImageDownsamplingTooLargeError(PeteError):
  pass


class UnapprovedDicomStoreError(PeteError):
  pass


class UnapprovedGcsBucketError(PeteError):
  pass


class PatchDimensionsDoNotMatchEndpointInputDimensionsError(PeteError):
  pass
