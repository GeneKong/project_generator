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
import yaml,re

from .settings import ProjectSettings
from .util import flatten, uniqify, load_yaml_records
from .project import *

class Generator:
    def __init__(self, args):
        # first read all project settings, then replace project.yaml's variables.
        try:
            with open(args.settings, 'rt') as f:
                self.settings_dict = yaml.load(f)
        except IOError:
            pass
        # all {var} will try to repalced.
        pattern = re.compile(r'{(.*?)}')
        yaml.add_implicit_resolver("!uservar", pattern)

        def userVar_sub(matchobj):
            if matchobj.group(1) in self.settings:
                return self.settings[matchobj.group(1)]
            else :
                return matchobj.group(0)

        def uservar_constructor(loader, node):
            value = loader.construct_scalar(node)
            return re.sub(pattern, userVar_sub, value)

        yaml.add_constructor("!uservar", uservar_constructor)

        if type(args.file) is not dict:
            try:
                with open(args.file, 'rt') as f:
                    self.projects_dict = yaml.load(f)
            except IOError:
                raise IOError("The main progen projects file %s doesn't exist." % args.file)
        else:
            self.projects_dict = args.file
        self.workspaces = {}
        self.settings = ProjectSettings()

        if 'settings' in self.projects_dict:
            self.settings.update(self.projects_dict['settings'])

    def generate(self, name=''):
        found = False
        if name != '':
            # process project first, workspaces afterwards
            if 'projects' in self.projects_dict:
                if name in self.projects_dict['projects'].keys():
                    found = True
                    records = self.projects_dict['projects'][name]
                    yield Project(name, load_yaml_records(uniqify(flatten(records))), self.settings)
            if 'workspaces' in self.projects_dict:
                workspace_settings = {}
                if name in self.projects_dict['workspaces'].keys():
                    found = True
                    records = self.projects_dict['workspaces'][name]
                    if 'settings' in records:
                        workspace_settings = records['settings'] 
                    projects = [Project(project, load_yaml_records(uniqify(flatten(self.projects_dict['projects'][project]))), self.settings, name) for project in records['projects']]
                    self.workspaces[name] = ProjectWorkspace(name, projects, self.settings, workspace_settings)
                    yield self.workspaces[name]
        else:
            if 'projects' in self.projects_dict:
                found = True
                for name, records in sorted(self.projects_dict['projects'].items(),
                                            key=lambda x: x[0]):
                    yield Project(name, load_yaml_records(uniqify(flatten(records))), self.settings)
            if 'workspaces' in self.projects_dict:
                found = True
                for name, records in sorted(self.projects_dict['workspaces'].items(),
                                            key=lambda x: x[0]):
                    workspace_settings = {}
                    if 'settings' in records:
                        workspace_settings = records['settings']
                    projects = [Project(project, load_yaml_records(uniqify(flatten(self.projects_dict['projects'][project]))), self.settings, name) for project in records['projects']]
                    self.workspaces[name] = ProjectWorkspace(name, projects, self.settings, workspace_settings)
                    yield self.workspaces[name]

        if not found:
            logging.error("You specified an invalid project name.")
