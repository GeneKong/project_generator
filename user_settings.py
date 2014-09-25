# Copyright 2014 0xc0170
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
import os

FROMELF = 'fromelf'
UV4 = r'C:\Keil_v5\UV4\UV4.exe'
IARBUILD = r'C:\Program Files (x86)\IAR Systems\Embedded Workbench 7.0\common\bin\IarBuild.exe'

if os.name == "posix":
    # Expects either arm-none-eabi to be installed here, or
    # even better, a symlink from /usr/local/arm-none-eabi to the most recent
    # version.
    gcc_bin_path = "/usr/local/arm-none-eabi/bin/"
elif os.name == "nt":
    gcc_bin_path = ""