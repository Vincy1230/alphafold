# Copyright 2025 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""pytest 固件。

该固件用于在运行测试前解析 absl flags。
"""

import sys

from absl import flags
import pytest


@pytest.fixture(scope="session", autouse=True)
def initialize_absl_flags(request):
  del request
  # 将命令行中 absl 可识别的参数解析为 absl flags。
  flags.FLAGS(sys.argv, known_only=True)
