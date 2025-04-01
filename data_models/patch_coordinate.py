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

"""Shared dataclasses across requests and responses for Pete."""

import dataclasses

import pete_errors


@dataclasses.dataclass(frozen=True)
class PatchCoordinate:
  """A coordinate of a patch."""

  x_origin: int
  y_origin: int
  height: int
  width: int

  def __post_init__(self):
    if (self.width != 224 or self.height != 224):
      raise pete_errors.PatchDimensionsDoNotMatchEndpointInputDimensionsError(
          'Patch coordinate width and height must be', f' 224x224.'
      )


def create_patch_coordinate(
    x_origin: int,
    y_origin: int,
    width: int = -1,
    height: int = -1,
) -> PatchCoordinate:
  """Creates a patch coordinate."""
  if width == -1:
    width = 224
  if height == -1:
    height = 224
  return PatchCoordinate(
      x_origin=x_origin,
      y_origin=y_origin,
      width=width,
      height=height,
  )
