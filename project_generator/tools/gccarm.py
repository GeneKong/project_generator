# Copyright 2014-2015 0xc0170
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

from copy import deepcopy
import logging

from .makefile import MakefileTool

logger = logging.getLogger('progen.tools.gccarm')

class MakefileGccArm(MakefileTool):

    def __init__(self, workspace, env_settings):
        MakefileTool.__init__(self, workspace, env_settings, logging)

    @staticmethod
    def get_toolnames():
        return ['gcc_arm']

    @staticmethod
    def get_toolchain():
        return 'gcc_arm'

    def export_project(self):
        """ Processes misc options specific for GCC ARM, and run generator """
        generated_projects = deepcopy(self.generated_projects)
        self.process_data_for_makefile(self.workspace)
        generated_projects['path'], generated_projects['files']['makefile'] = self.gen_file_jinja('makefile_gcc.tmpl', self.workspace, 'Makefile', self.workspace['output_dir']['path'])
        return generated_projects

    def process_data_for_makefile(self, project_data):
        project_data['toolchain'] = 'arm-none-eabi-'
        project_data['toolchain_bin_path'] = self.env_settings.get_env_settings('gcc')
        MakefileTool.process_data_for_makefile(self, project_data)
