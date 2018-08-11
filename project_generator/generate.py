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
import yaml,os,copy,logging
        
from .settings import ProjectSettings
from .util import fix_properties_in_context, merge_without_override
from .project import Project

class Generator:
    def __init__(self, source):
        self.basepath = os.path.dirname(source)
        if len(self.basepath) == 0:
            self.basepath = "."
        self.properties = {}
        try:
            with open(source, 'rt') as f:
                self.projects_dict = yaml.load(f)
                if 'properties' in self.projects_dict:
                    self.properties = self.projects_dict['properties']                    
                    self.projects_dict = fix_properties_in_context(self.projects_dict, self.properties)
        except IOError:
            raise IOError("The main progen projects file %s doesn't exist." % source)
        self.settings = ProjectSettings()
        # origin properties backup in settings
        self.settings.properties = copy.deepcopy(self.properties)

        if 'settings' in self.projects_dict:
            self.settings.update(self.projects_dict['settings'])
    
    def _generate_subproj(self, project):
        """ don't generate src project """
        for k, sproj in project.sub_projects.items():
            if sproj.project['type'].lower() != "src":
                yield sproj
                self._generate_subproj(sproj)
    
    def generate(self, name='', tool='gnu_mcu_eclipse'):
        found = False
        if name != '':
            # process project first, workspaces afterwards
            if 'projects' in self.projects_dict:
                if name in self.projects_dict['projects'].keys():
                    found = True
                    records = self.projects_dict['projects'][name]
                    self.reset_properties()
                    project = Project(name, tool, records,  self.settings, self)
                    yield project
                    for sproj in self._generate_subproj(project):
                        yield sproj
        else:
            if 'projects' in self.projects_dict:
                found = True
                for name, records in sorted(self.projects_dict['projects'].items(),
                                            key=lambda x: x[0]):
                    self.reset_properties()
                    if not records:
                        records = {}
                    project = Project(name, tool, records, self.settings, self)
                    yield project
                    for sproj in self._generate_subproj(project):
                        yield sproj

        if not found:
            logging.error("You specified an invalid project name.")

    def reset_properties(self):
        """
        reset root project properties
        """
        self.properties = copy.deepcopy(self.settings.properties)
        
    def merge_properties_without_override(self, prop_dict):
        """
        update properties when parser sub-project and required project
        """
        for key, value in prop_dict.items():
            if type(value) is dict:
                if key in self.properties:
                    merge_without_override(self.properties[key], value)
                else:
                    self.properties[key] = value
            elif key not in self.properties:
                self.properties[key] = value
                

# all {var} will try to repalced, yaml can't work good for parse
"""
def userVar_sub(matchobj):
    if matchobj.group(1) in Generator.properties:
        return Generator.properties[matchobj.group(1)]
    else :
        return matchobj.group(0)

def uservar_constructor(loader, node):
    value = loader.construct_scalar(node)
    return re.sub(r'\${(.*?)}', userVar_sub, value)

yaml.add_constructor("!uservar", uservar_constructor)
yaml.add_implicit_resolver("!uservar", re.compile(r'^(.*)\${(.*?)}(.*)$'))
"""