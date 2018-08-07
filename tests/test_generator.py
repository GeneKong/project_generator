# Copyright 2015 0xc0170
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
import shutil

import yaml
from unittest import TestCase

from project_generator.generate import Generator

project_1_yaml = {
    'files': {
        'sources': ['sources/main.cpp',
                    'sources/${prop_1}_alter.c',
                    'sources/${prop_1_1}/${prop_2_1}_favors.c',],
        'includes': ['includes/${prop_2}.h']
    },
    'favor_dimensions': ['dim_1', 'dim_2'],
    'project_favors' : {
        'favor_1_1': {
            'dimension': 'dim_1',
            'properties': { 
                'prop_1_1':'1_1'
            }
        },
        'favor_1_2': {
            'dimension': 'dim_1',
            'properties': { 
                'prop_1_1':'1_2'
            }
        },
        'favor_2_1': {
            'dimension': 'dim_2',
            'properties': { 
                'prop_2_1':'2_1'
            }
        },
        'favor_2_2': {
            'dimension': 'dim_2',
            'properties': { 
                'prop_2_1':'2_2'
            }
        },
    },
    'properties' : {
        'prop_1':'pabc',
        'prop_2':'pl1'
    }
}

projects_yaml = {
    'projects': {
        'project_1' : {
            'favor': {
                'dim_1':'favor_1_1',
                'dim_2':'favor_2_2'
                }
            }
    },
    'settings' : {
        'export_dir': ['not_generated_projects']
    }
}

class TestGenerator(TestCase):

    """test things related to the PgenWorkspace class"""

    def setUp(self):
        if not os.path.exists('test_workspace'):
            os.makedirs('test_workspace')
        if not os.path.exists('test_workspace/project_1'):
            os.makedirs('test_workspace/project_1')
        # write project file
        with open(os.path.join(os.getcwd(), 'test_workspace/project_1/module.yaml'), 'wt') as f:
            f.write(yaml.dump(project_1_yaml, default_flow_style=False))
        # write projects file
        with open(os.path.join(os.getcwd(), 'test_workspace/projects.yaml'), 'wt') as f:
            f.write(yaml.dump(projects_yaml, default_flow_style=False))
        self.workspace = Generator('test_workspace/projects.yaml')
        for project in self.workspace.generate():
            print(project.name)

    def tearDown(self):
        # remove created directory
        shutil.rmtree('test_workspace', ignore_errors=True)

    def test_settings(self):
        # only check things which are affected by projects.yaml
        assert self.workspace.settings.export_location_format == 'not_generated_projects'
