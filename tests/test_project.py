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

from project_generator.project import Project
from project_generator.generate import Generator
from project_generator.settings import ProjectSettings
from project_generator.util import merge_recursive

project_1_yaml = {
    'name': 'project_1',
    'type': 'exe',    
    'tools_supported': ['iar_arm', 'uvision', 'coide', 'unknown'],
    'files': {
        'sources': { 'sources_dict' : ['src/main.cpp']
        },
        'includes': ['src/header1.h'],
    },
    'common': {
        'flags': ['-mcpu=cortex-m4', '-mthumb'],
        'macros': ['MACRO1', 'MACRO2', None],
    },
    'cxxcompile': {
        'flags': ['-std=gnu++11']
    },
    'linker': {
        'search_paths': ['ldscripts', 'staticlib'],
        'script_files': ['linker.ld'],
        'libraries': ['feThirdLib']
    },
    'required': {
        'project_2' : {},
        'project_3' : {}
    }
}

project_2_yaml = {
    'name': 'project_2',
    'type': 'lib',    
    'tools_supported': ['iar_arm', 'uvision', 'coide', 'unknown'],
    'files': {
        'sources': { 
            'sources_dict' : ['source/file2.cpp'],
            'sources_dict2' : ['source/file3.cpp']
        },
        'includes':  {
            'include_dict' : ['include/header2.h'],
            'include_dict2' : ['include/header3.h']
        }
    },
    'common':
    {
        'macros': ['MACRO2_1', 'MACRO2_2'],
    },
    'required': {
        'project_4' : {},    
    },
    'protable': {
        'dest': 'project_4',
        'port': ['port/port.c'],
        'config': ['include/config_1.config', 'include/config_2.config']
    }
}

project_3_yaml = {
    'name': 'project_3',
    'type': 'src',
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

project_4_yaml = {
    'name': 'project_4',
    'type': 'src',        
    'files': {
        'sources': { 
            'sources_dict' : ['source/file2.cpp'],
            'sources_dict2' : ['source/file3.cpp']
        },
        'includes':  {
            'include_dict' : ['include/header2.h'],
            'include_dict2' : ['include/header3.h']
        }
    },
    'common':
    {
        'macros': ['MACRO2_1', 'MACRO2_2'],
    }
}

projects_yaml = {
    'projects': {
        'project_1' : {
            'properties': {
                'prop_1':'override_1',
            },
            'favor': {
                'dim_1':'favor_1_2',
                'dim_2':'favor_2_1'
            }
        }
    },
    'settings' : {
        'export_dir': ['projects/{tool}_{target}/{project_name}']
    }
}

def init_files():
    create_dirs = [
        'test_workspace',
        'test_workspace/project_1',
        'test_workspace/project_1/src',
        'test_workspace/project_1/ldscripts',
        'test_workspace/project_1/staticlib',            
        'test_workspace/project_2',
        'test_workspace/project_2/include',
        'test_workspace/project_2/source',
        'test_workspace/project_2/port',
        'test_workspace/project_3',
        'test_workspace/project_3/includes',
        'test_workspace/project_3/sources',
        'test_workspace/project_3/sources/1_1',
        'test_workspace/project_3/sources/1_2',
        'test_workspace/project_4',
        'test_workspace/project_4/include',
        'test_workspace/project_4/source',
        ]
    for cdir in create_dirs:
        if not os.path.exists(cdir):
            os.makedirs(cdir)
            
    create_files = [
        'test_workspace/project_1/src/header1.h',
        'test_workspace/project_1/src/main.cpp',
        'test_workspace/project_1/ldscripts/linker.ld',
        'test_workspace/project_1/staticlib/feThirdLib.a',
        'test_workspace/project_2/include/header2.h',
        'test_workspace/project_2/include/header3.h',
        'test_workspace/project_2/source/file2.cpp',
        'test_workspace/project_2/source/file3.cpp',
        'test_workspace/project_2/include/config_1.config',
        'test_workspace/project_2/include/config_2.config',
        'test_workspace/project_2/port/port.c',
        'test_workspace/project_3/includes/pl1.h',
        'test_workspace/project_3/sources/pabc_alter.c',
        'test_workspace/project_3/sources/override_1_alter.c',
        'test_workspace/project_3/sources/1_1/2_1_favors.c',
        'test_workspace/project_3/sources/1_1/2_2_favors.c',
        'test_workspace/project_3/sources/1_2/2_1_favors.c',
        'test_workspace/project_3/sources/1_2/2_2_favors.c',           
        'test_workspace/project_3/sources/main.cpp',
        'test_workspace/project_4/include/header2.h',
        'test_workspace/project_4/include/header3.h',
        'test_workspace/project_4/source/file2.cpp',
        'test_workspace/project_4/source/file3.cpp',
        ]
    for cfile in create_files:
        with open(os.path.join(os.getcwd(), cfile), 'wt') as f:
            pass

def test_output_directory_formatting():
    path, depth = Project._generate_output_dir(ProjectSettings(),'aaa/bbb/cccc/ddd/eee/ffff/ggg')

    assert depth == 7
    assert os.path.normpath(path) == os.path.normpath('../../../../../../../')

class TestProjectYAML(TestCase):

    """test things related to the Project class"""

    def setUp(self):
        init_files()
            
        # write project file
        with open(os.path.join(os.getcwd(), 'test_workspace/project_1/module.yaml'), 'wt') as f:
            f.write(yaml.dump(project_1_yaml, default_flow_style=False))
        with open(os.path.join(os.getcwd(), 'test_workspace/project_2/module.yaml'), 'wt') as f:
            f.write(yaml.dump(project_2_yaml, default_flow_style=False))
        with open(os.path.join(os.getcwd(), 'test_workspace/project_3/module.yaml'), 'wt') as f:
            f.write(yaml.dump(project_3_yaml, default_flow_style=False))
        with open(os.path.join(os.getcwd(), 'test_workspace/project_4/module.yaml'), 'wt') as f:
            f.write(yaml.dump(project_4_yaml, default_flow_style=False))
        # write projects file
        with open(os.path.join(os.getcwd(), 'test_workspace/projects.yaml'), 'wt') as f:
            f.write(yaml.dump(projects_yaml, default_flow_style=False))

        # now that Project and PgenWorkspace accepts dictionaries, we dont need to
        # create yaml files!
        self.project = next(Generator('test_workspace/projects.yaml').generate('project_1'))

    def tearDown(self):
        # remove created directory
        shutil.rmtree('test_workspace', ignore_errors=True)

    def test_project_yaml(self):
        # test using yaml files and compare basic data
        project = next(Generator('test_workspace/projects.yaml').generate('project_1'))
        assert self.project.name == project.name
        # fix this one, they should be equal
        #self.assertDictEqual(self.project.project, project.project)

    def test_name(self):
        assert self.project.name == 'project_1'

    def test_project_attributes(self):
        self.project._fill_export_dict('uvision')
        assert set(self.project.project['export']['macros'] + [None]) & set(project_1_yaml['common']['macros'] + project_2_yaml['common']['macros']) 
        assert set(self.project.project['export']['include_files'].keys()) & set(['default'] + list(project_2_yaml['common']['includes'].keys()))

        # no c or asm files, empty dics
        assert self.project.project['export']['source_files_c'] == dict()
        assert self.project.project['export']['source_files_s'] == dict()
        # source groups should be equal
        assert self.project.project['export']['source_files_cpp'].keys() == merge_recursive(project_1_yaml['common']['sources'], project_2_yaml['common']['sources']).keys()

    def test_copy(self):
        # test copy method which should copy all files to generated project dir by default
        self.project._fill_export_dict('uvision', True)
        self.project._copy_sources_to_generated_destination()

    def test_set_output_dir_path(self):
        self.project._fill_export_dict('uvision')
        assert self.project.project['export']['output_dir']['path'] == os.path.join('projects', 'uvision_target1','project_1')
