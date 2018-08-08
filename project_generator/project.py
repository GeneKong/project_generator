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

import os
import shutil
import logging
import operator
import copy
import yaml

from .tools_supported import ToolsSupported
from .tools.tool import get_tool_template
from .util import merge_recursive, PartialFormatter, FILES_EXTENSIONS, VALID_EXTENSIONS, FILE_MAP, SOURCE_KEYS, fix_paths, merge_without_override

logger = logging.getLogger('progen.project')

class ProjectTemplate:
    """ Public data which can be set in yaml files
        Yaml data available are:
            *** project profile ***
            'name': name,               # project name
            'type': type,               # project type
            'templates': [],            # templates
            'required': {},             # required project/lib/src
            
            *** dimensisons/favors ***
            'favor_dimensions' : [xx, yy]
            'project_favors': {
                '' : {
                    'dimension' : xx
                    *** properties ***
                    'properties': {}
                    *** files ***
                    *** compile options ***
                }                
            }
            
            *** files ***
            'includes': {},
            'sources': {},
            
            *** compile options ***
            'common': {
                    'flags': []
                    'macros': []
                    },
            'assemble': {
            
            },
            'ccompile': {
            },
            'cxxcompile': {
            },
            'linker': {
                'flags':[],
                'script_files': []
                'search_paths': []
                'libraries': []
            },
            *** properties ***
            'properties': {}
    """

    @staticmethod
    def _get_common_data_template():
        """ Data for common """

        data_template = {
            'common': {
                'flags': [],
                'macros': []
            },
            'assemble': {
                'flags': [],
                'macros': []
            },
            'ccompile': {
                'flags': [],
                'macros': []
            },
            'cxxcompile': {
                'flags': [],
                'macros': []
            },
            'linker': {
                'flags':[],
                'script_files': [],
                'search_paths': [],
                'libraries': []
            },
            'files': {
                'includes': {},
                'sources': {}
            }
        }
        return data_template

    @staticmethod
    def get_project_template(name="Default", output_type='exe', debugger=None, build_dir='build'):
        """ Project data (+ data) """

        project_template = {
            'build_dir' : build_dir,  # Build output path
            'debugger' : debugger,    # Debugger
            'export_dir': '',         # Export directory path
            'name': name,             # project name
            'type': output_type,      # output type, default - exe
            'templates': [],          # templates
            'tool_specific':{},       # 
            'required': {},           # Tools which are supported,
        }
        project_template.update(ProjectTemplate._get_common_data_template())
        return project_template

class Project:

    """ Represents a project, which can be formed of many yaml files """

    def __init__(self, name, project_dicts, settings, gen, parent = None):
        """ Initialise a project with a yaml file """

        assert type(project_dicts) is dict, "Project records/dics must be a dict" % project_dicts 

        self.settings = settings
        self.name = name
        self.parent = parent
        self.basepath = os.path.sep.join([gen.basepath, name])
        if 'favor' in project_dicts:
            self.favors = project_dicts['favor']
        else:
            self.favors = {}
        if 'properties' in project_dicts:
            gen.merge_properties_without_override(project_dicts['properties'])
            
        self.project = ProjectTemplate.get_project_template(self.name)
        
        try:
            with open(os.path.sep.join([self.basepath, "module.yaml"]), 'rt') as f:
                need_reload = False
                self.src_dicts = yaml.load(f)
                if 'properties' in self.src_dicts:
                    gen.merge_properties_without_override(self.src_dicts['properties'])
                    need_reload = True
                if 'favor_dimensions' in self.src_dicts:
                    #process favor context
                    for dim in self.src_dicts['favor_dimensions']:
                        if dim not in self.favors:
                            raise NameError ("%s in favor_dimensions not set for project %s." % (dim, name))
                        else:
                            favor = self.src_dicts['project_favors'][self.favors[dim]]
                            if favor['dimension'] != dim :
                                raise NameError ("project_favors %s's dimension:%s, is not %s." %
                                                 (self.favors[dim], favor['dimension'], dim))
                            for key in favor :
                                if key == 'properties':
                                    gen.merge_properties_without_override(favor['properties'])
                                    need_reload = True
                                elif key == 'dimension':
                                    pass
                                elif key in self.project:
                                    self.project[key] = Project._dict_elim_none(merge_recursive(self.project[key], favor[key]))  
                if need_reload:
                    f.seek(0)
                    self.src_dicts = yaml.load(f)
        except IOError:
            raise IOError("The module.yaml in project:%s doesn't exist." % self.name)

        self._update_from_src_dict(self.src_dicts)
        
        if self.project['type'].lower() == 'src':
            if self.parent:
                self.parent.update_from_required(self)
            else:
                raise NameError ("'src' type project %s can't be root project." % (name))
        
        #Process required project
        self.sub_projects = {}
        for subproj in self.project['required']:            
            gen.reset_properties()
            merge_without_override(self.project['required'][subproj], project_dicts)
            self.sub_projects[subproj] = Project(subproj, self.project['required'][subproj], settings, gen, self)
            if self.project['type'].lower() == 'src'and self.sub_projects[subproj].project['type'].lower() != 'src':
                raise NameError ("'src' type project %s required project must be 'src' type, but %s not." % (name, subproj))
            
        self.generated_files = {}
    
    def _update_from_src_dict(self, src_dict, override_str = True):
        for key in src_dict:
            if key in ['favor_dimensions', 'project_favors']:
                continue
            elif key == 'files':
                for ikey in self.project[key]:                
                    if ikey in src_dict[key]:
                        self._process_files_item(ikey, src_dict)
            elif key in self.project:
                if type(self.project[key]) is dict:
                    self.project[key] = Project._dict_elim_none(merge_recursive(self.project[key], src_dict[key]))
                elif  type(self.project[key]) is list:
                    self.project[key] = Project._list_elim_none(merge_recursive(self.project[key], src_dict[key]))
                elif override_str:
                    self.project[key] = src_dict[key]
        
    def update_from_required(self, subproj):
        """
        update information from sub-src-project  
        """
        if self.project['type'].lower() == 'src':
            self.parent.update_from_required(subproj)
        
        #Need update for PATH
        src_project = copy.deepcopy(subproj.project)
        for key in ["tool_specific", "templates", "files", "linker"]:
            pass
        
        if "search_paths" in src_project["linker"]:
            src_project["linker"]["search_paths"] = []
            for path in subproj.project["linker"]["search_paths"]:
                if os.path.exists(path):
                    src_project["linker"]["search_paths"].append(path)
                else:
                    src_project["linker"]["search_paths"].append(os.path.join("..", subproj.name, path))                
        if "files" in src_project:
            src_project["files"]["includes"] = {}
            for key, value in subproj.project["files"]["includes"].items():
                src_project["files"]["includes"][key] = []
                for path in value:
                    if os.path.exists(path):
                        src_project["files"]["includes"][key].append(path)
                    else:
                        src_project["files"]["includes"][key].append(os.path.join("..", subproj.name, path))
            for key, value in subproj.project["files"]["sources"].items():
                src_project["files"]["sources"][key] = []
                for path in value:
                    if os.path.exists(path):
                        src_project["files"]["sources"][key].append(path)
                    else:
                        src_project["files"]["sources"][key].append(os.path.join("..", subproj.name, path))                
        if "tool_specific" in src_project:
            for key, value in subproj.project["tool_specific"].items():
                if "includes" in value:
                    if type(value["includes"]) is list:
                        src_project["tool_specific"][key]["includes"] = []
                        for path in value["includes"]:
                            if os.path.exists(path):
                                src_project["tool_specific"][key]["includes"].append(path)
                            else:
                                src_project["tool_specific"][key]["includes"].append(os.path.join("..", subproj.name, path))
                    elif type(value["includes"]) is dict:
                        src_project["tool_specific"][key]["includes"] = {}
                        for k,v in value["includes"].items():
                            src_project["tool_specific"][key]["includes"][k] = []
                            for path in v:
                                if os.path.exists(path):
                                    src_project["tool_specific"][key]["includes"][k].append(path)
                                else:
                                    src_project["tool_specific"][key]["includes"][k].append(os.path.join("..", subproj.name, path))
                elif "sources" in value:
                    if type(value["sources"]) is list:
                        src_project["tool_specific"][key]["sources"] = []
                        for path in value["sources"]:
                            if os.path.exists(path):
                                src_project["tool_specific"][key]["sources"].append(path)
                            else:
                                src_project["tool_specific"][key]["sources"].append(os.path.join("..", subproj.name, path))
                    elif type(value["sources"]) is dict:
                        src_project["tool_specific"][key]["sources"] = {}
                        for k,v in value["sources"].items():
                            src_project["tool_specific"][key]["sources"][k] = []
                            for path in v:
                                if os.path.exists(path):
                                    src_project["tool_specific"][key]["sources"][k].append(path)
                                else:
                                    src_project["tool_specific"][key]["sources"][k].append(os.path.join("..", subproj.name, path))
        
        self._update_from_src_dict(src_project, False)
    
    def _process_files_item(self, key, src_dicts):
        if type(src_dicts['files'][key]) is list:
            self.project['files'][key].setdefault('default',[]).extend(src_dicts['files'][key])
        else:
            self.project['files'][key] = Project._dict_elim_none(
                merge_recursive(
                    self.project['files'][key],
                    src_dicts['files'][key]))
                    
    @staticmethod
    def _list_elim_none(list_to_clean):
        return [l for l in list_to_clean if l]

    @staticmethod
    def _dict_elim_none(dic_to_clean):
        dic = dic_to_clean
        try:
            for k, v in dic_to_clean.items():
                if type(v) is list:
                    dic[k] = Project._list_elim_none(v)
                elif type(v) is dict:
                    dic[k] = Project._dict_elim_none(v)
        except AttributeError:
            pass
        return dic                                

    def _set_internal_files_data(self):
        # process here includes, sources and set all internal data related to them
        self._process_source_files(self.project['files']['sources'])
        self._process_include_files(self.project['files']['includes'])

    def _set_internal_tool_data(self, tool_keywords):
        # process here includes, sources and set all internal data related to them for tool_keywords
        for tool in tool_keywords:
            if tool in self.project['tool_specific'].keys():
                if 'includes' in self.project['tool_specific'][tool]:
                    for files in self.project['tool_specific'][tool]['includes']:
                        self._process_include_files(files)
                if 'sources' in self.project['tool_specific'][tool]:
                    for files in self.project['tool_specific'][tool]['sources']:
                        self._process_source_files(files)

    def _set_internal_macros_and_flags(self):
        self.export['macros']['common'] = merge_recursive([], self.project['common']['macros'])
        self.export['macros']['assemble'] = merge_recursive([], self.project['assemble']['macros'])
        self.export['macros']['ccompile'] = merge_recursive([], self.project['ccompile']['macros'])
        self.export['macros']['cxxcompile'] = merge_recursive([], self.project['cxxcompile']['macros'])
        self.export['macros'] = Project._dict_elim_none(self.export['macros'])
        
        self.export['compile_flags']['common'] = merge_recursive([], self.project['common']['flags'])
        self.export['compile_flags']['assemble'] = merge_recursive([], self.project['assemble']['flags'])
        self.export['compile_flags']['ccompile'] = merge_recursive([], self.project['ccompile']['flags'])
        self.export['compile_flags']['cxxcompile'] = merge_recursive([], self.project['cxxcompile']['flags'])
        self.export['compile_flags'] = Project._dict_elim_none(self.export['compile_flags'])
                
    def _process_include_files(self, files, use_group_name = 'default'):
        # If it's dic add it , if file, add it to files
        use_includes = []
        if type(files) == dict:
            for group_name, include_files in files.items():
                self._process_include_files(include_files, group_name)
        elif type(files) == list:
            use_includes = files
        else:
            if files:
                use_includes = [files]

        if use_group_name not in self.export['include_files'] and use_includes:
            self.export['include_files'][use_group_name] = []

        for include_file in use_includes:
            include_file = include_file.replace('\\', '/')
            # include might be set to None - empty yaml list
            if include_file:
                if os.path.isdir(include_file):
                    # its a directory
                    dir_path = include_file
                    # get all files from dir
                    include_files = []
                    try:
                        for f in os.listdir(dir_path):
                            if os.path.isfile(os.path.join(os.path.normpath(dir_path), f)) and f.split('.')[-1].lower() in FILES_EXTENSIONS['include_files']:
                                include_files.append(os.path.join(os.path.normpath(dir_path), f))
                    except:
                        # TODO: catch only those exceptions which are relevant
                        logger.debug("The includes is not accessible: %s" % include_file)
                        continue
                    self.export['include_files'][use_group_name] += include_files
                else:
                    # include files are in groups as sources
                    self.export['include_files'][use_group_name].append(os.path.normpath(include_file))
                    dir_path = os.path.dirname(include_file)
                if not os.path.normpath(dir_path) in self.export['include_paths']:
                    self.export['include_paths'].append(os.path.normpath(dir_path))

    def _process_source_files(self, files, use_group_name='default'):
        use_sources = []
        if type(files) == dict:
            for group_name, sources in files.items():
                # process each group name as separate entity
                self._process_source_files(Project._list_elim_none(sources), group_name)
        elif type(files) == list:
            use_sources = Project._list_elim_none(files)
        else:
            if files:
                use_sources = [files]

        for source_file in use_sources:
            source_file = source_file.replace('\\', '/')
            source_file = os.path.normpath(source_file)
            if os.path.isdir(source_file):
                self.export['source_paths'].append(source_file)
                self._process_source_files([os.path.join(source_file, f) for f in os.listdir(
                    source_file) if os.path.isfile(os.path.join(source_file, f))], use_group_name)

            # Based on the extension, create a groups inside source_files_(extension)
            extension = source_file.split('.')[-1].lower()
            if extension not in VALID_EXTENSIONS:
                continue
            source_group = FILE_MAP[extension]
            if use_group_name not in self.export[source_group]:
                self.export[source_group][use_group_name] = []

            self.export[source_group][use_group_name].append(source_file)

            if not os.path.dirname(source_file) in self.export['source_paths']:
                self.export['source_paths'].append(os.path.normpath(os.path.dirname(source_file)))

    @staticmethod
    def _generate_output_dir(settings, path):
        """ This is a separate function, so that it can be more easily tested """

        relpath = os.path.relpath(settings.root,path)
        count = relpath.count(os.sep) + 1

        return relpath+os.path.sep, count

    def _get_tool_data(self, key, tool_keywords):
        data = []
        for tool_name in tool_keywords:
            try:
                if self.project['tool_specific'][tool_name][key]:
                    if type(self.project['tool_specific'][tool_name][key]) is list:
                        data += self.project['tool_specific'][tool_name][key]
                    else:
                        data.append(self.project['tool_specific'][tool_name][key])
            except KeyError:
                continue
        return data

    def _get_tool_sources(self, tool_keywords):
        sources = {}
        for source_key in SOURCE_KEYS:
            sources[source_key] = {}
            for tool_name in tool_keywords:
                try:
                    sources[source_key] = merge_recursive(sources[source_key], self.project['tool_specific'][tool_name][source_key])
                except KeyError:
                    continue
        return sources

    def _get_tool_includes(self, tool_keywords):
        include_files = {}
        for tool_name in tool_keywords:
            try:
                include_files = merge_recursive(include_files, self.project['tool_specific'][tool_name]['include_files'])
            except KeyError:
                continue
        return include_files

    def _set_output_dir_path(self, tool, copied):
        if self.settings.export_location_format != self.settings.DEFAULT_EXPORT_LOCATION_FORMAT:
            location_format = self.settings.export_location_format
        else:
            if 'export_dir' in self.export and self.export['export_dir']:
                location_format = self.export['export_dir']
            else:
                location_format = self.settings.export_location_format

        # substitute all of the different dynamic values
        location = PartialFormatter().format(location_format, **{
            'project_name': self.name,
            'tool': tool,
        })

        self.export['output_dir']['path'] = os.path.normpath(location)
        path = self.export['output_dir']['path']
        if copied:
            # Sources were copied, therefore they should be in the exported folder
            self.export['output_dir']['rel_path'] = ''
            self.export['output_dir']['rel_count'] = 0
        else:
            self.export['output_dir']['rel_path'], self.export['output_dir']['rel_count'] = self._generate_output_dir(self.settings, path)

    def _fill_export_dict(self, tool, copied=False):
        tool_keywords = []
        # get all keywords valid for the tool
        tool_keywords.append(ToolsSupported().get_toolchain(tool))
        tool_keywords += ToolsSupported().get_toolnames(tool)
        tool_keywords = list(set(tool_keywords))

        # Set the template keys an get the relative path to fix all paths
        self.export = get_tool_template()

        self._set_output_dir_path(tool, copied)

        self._set_internal_files_data()
        self._set_internal_tool_data(tool_keywords)
        self._set_internal_macros_and_flags()

        # Merge common project data with tool specific data
        self.export['template'] = self._get_tool_data('template', tool_keywords)
        self.export['linker_search_paths'] = self.project['linker']['search_paths']
        self.export['linker'] = self.project['linker']
        self.export['output_type'] = self.project['type']
        
        fix_paths(self.export, self.export['output_dir']['rel_path'],
                   list(FILES_EXTENSIONS.keys()) + ['include_paths', 'source_paths', 'linker_search_paths'])

        # misc for tools requires dic merge
        misc = self._get_tool_data('misc', tool_keywords)
        for m in misc:
            self.export['misc'] = merge_recursive(self.export['misc'], m)

        # This is magic with sources/include_files as they have groups
        tool_sources = self._get_tool_sources(tool_keywords)
        for key in SOURCE_KEYS:
            self.export[key] = merge_recursive(self.export[key], tool_sources[key])
            # sort all sources within its own group and own category (=k)
            # the tool needs to do sort files as tools require further processing based on 
            # categories (we can't mix now cpp and c files for instance)
            for k, v in self.export[key].items():
                self.export[key][k] = sorted(v, key=lambda x: os.path.basename(x))

        self.export['include_files'] = merge_recursive(self.export['include_files'], self._get_tool_includes(tool_keywords))

        # linker checkup
        if self.export['output_type'] != 'src' and len(self.export['linker']['script_files']) == 0 :
            logger.debug("Executable - no linker command found.")

    def _copy_sources_to_generated_destination(self):
        """ Copies all project files to specified directory - generated dir """

        files = []
        for key in FILES_EXTENSIONS.keys():
            if key in self.export:
                if type(self.export[key]) is dict:
                    for k,v in self.export[key].items():
                        files.extend(v)
                elif type(self.export[key]) is list:
                    files.extend(self.export[key])
                else:
                    files.append(self.export[key])

        destination = os.path.join(self.settings.root, self.export['output_dir']['path'])
        if os.path.exists(destination):
            shutil.rmtree(destination)
        for item in files:
            s = os.path.join(self.settings.root, self.basepath, item)
            d = os.path.join(destination, item)
            if os.path.isdir(s):
                shutil.copytree(s,d)
            else:
                if not os.path.exists(os.path.dirname(d)):
                    os.makedirs(os.path.join(self.settings.root, os.path.dirname(d)))
                shutil.copy2(s,d)

    def clean(self, tool):
        """ Clean a project """

        tools = self._validate_tools(tool)
        if tools == -1:
            return -1

        for current_tool in tools:
            # We get the export dict formed, then use it for cleaning
            self._fill_export_dict(current_tool)
            path = self.export['output_dir']['path']

            if os.path.isdir(path):
                logger.info("Cleaning directory %s" % path)

                shutil.rmtree(path)
        return 0

    def generate(self, tool, copied=False, copy=False):
        """ Generates a project """

        tools = self._validate_tools(tool)
        if tools == -1:
            return -1

        generated_files = {}
        result = 0
        for export_tool in tools:
            exporter = ToolsSupported().get_tool(export_tool)

            # None is an error
            if exporter is None:
                result = -1
                logger.debug("Tool: %s was not found" % export_tool)
                continue

            self._fill_export_dict(export_tool, copied)
            if copy:
                logger.debug("Copying sources to the output directory")
                self._copy_sources_to_generated_destination()
            # dump a log file if debug is enabled
            if logger.isEnabledFor(logging.DEBUG):
                dump_data = {}
                dump_data['common'] = self.project['common']
                dump_data['tool_specific'] = self.project['tool_specific']
                dump_data['merged'] = self.export
                handler = logging.FileHandler(os.path.join(os.getcwd(), "%s.log" % self.name),"w", encoding=None, delay="true")
                handler.setLevel(logging.DEBUG)
                logger.addHandler(handler)
                logger.debug("\n" + yaml.dump(dump_data))

            files = exporter(self.export, self.settings).export_project()
            generated_files[export_tool] = files
        self.generated_files = generated_files
        return result

    def build(self, tool):
        """build the project"""

        tools = self._validate_tools(tool)
        if tools == -1:
            return -1

        result = 0

        for build_tool in tools:
            builder = ToolsSupported().get_tool(build_tool)
            # None is an error
            if builder is None:
                logger.debug("Tool: %s was not found" % builder)
                result = -1
                continue

            logger.debug("Building for tool: %s", build_tool)
            logger.debug(self.generated_files)
            if builder(self.generated_files[build_tool], self.settings).build_project() == -1:
                # if one fails, set to -1 to report
                result = -1
        return result

    def get_generated_project_files(self, tool):
        """ Get generated project files, the content depends on a tool. Look at tool implementation """

        exporter = ToolsSupported().get_tool(tool)
        return exporter(self.generated_files[tool], self.settings).get_generated_project_files()

