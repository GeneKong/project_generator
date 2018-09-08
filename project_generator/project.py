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
# import json

from .tools_supported import ToolsSupported
from .tools.tool import get_tool_template
from .util import merge_recursive, PartialFormatter, FILES_EXTENSIONS, VALID_EXTENSIONS, FILE_MAP, copytree, fix_paths, merge_without_override, fix_properties_in_context

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
            'asm': {
                'flags': [],
                'macros': []
            },
            'c': {
                'flags': [],
                'macros': []
            },
            'cxx': {
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
            },
        }
        return data_template
    @staticmethod
    def _get_tool_specific_template():
        return {
            'TargetOption':{},       # armcc            
            }
        
    @staticmethod
    def get_project_template(name="Default", output_type='exe', debugger=None, build_dir='build', port_dest = 'feConfig'):
        """ Project data (+ data) """

        project_template = {
            'build_dir' : build_dir,  # Build output path
            'debugger' : debugger,    # Debugger
            'export_dir': '',         # Export directory path
            'name': name,             # project name
            'type': output_type,      # output type, default - exe
            'templates': [],          # templates            
            'linker_search_paths': [],
            'lib_search_paths': [],
            'required': {},           # Tools which are supported,
            'portable':{
                'dest': port_dest,
                'config': {},
                'port': {}
            }
        }
        project_template.update(ProjectTemplate._get_common_data_template())
        project_template.update(ProjectTemplate._get_tool_specific_template())
        return project_template

class Project:

    """ Represents a project, which can be formed of many yaml files """

    def __init__(self, name, tool, project_dicts, settings, gen, parent = None):
        """ Initialise a project with a yaml file """

        if not project_dicts:
            project_dicts = {}
        assert type(project_dicts) is dict, "Project %s records/dics must be a dict" % (name, project_dicts) 

        tool_keywords = self._get_tool_keywords(tool)
        
        self.settings = settings
        self.name = name
        self.tool = tool
        self.parent = parent
        self.basepath = os.path.sep.join([gen.basepath, name])
        self.portable_dirs = []
        if 'favors' in project_dicts:
            self.favors = project_dicts['favors']
        else:
            self.favors = {}
        if 'properties' in project_dicts:
            gen.merge_properties_without_override(project_dicts['properties'])
            
        self.project = ProjectTemplate.get_project_template(self.name)
        
        try:
            with open(os.path.sep.join([self.basepath, "module.yaml"]), 'rt') as f:
                self.src_dicts = yaml.load(f)
                if 'tool_specific' in self.src_dicts:
                    for tool in self.src_dicts['tool_specific']:
                        if tool in tool_keywords:
                            for key in self.src_dicts['tool_specific'][tool]:
                                if key == 'properties':
                                    gen.merge_properties_without_override(self.src_dicts['tool_specific'][tool]['properties'])
                                elif key == 'files' :
                                    # files need careful merge
                                    for ikey in self.src_dicts['tool_specific'][tool][key]:
                                        self._process_files_item(ikey, self.src_dicts['tool_specific'][tool])
                                elif key in self.project:
                                    self.project[key] = Project._dict_elim_none(
                                        merge_recursive(self.project[key], self.src_dicts['tool_specific'][tool][key]))

                if 'favors' in self.src_dicts:
                    for key in self.src_dicts['favors']:
                        if key not in self.favors:
                            self.favors[key] = self.src_dicts['favors'][key]

                if 'properties' in self.src_dicts:
                    gen.merge_properties_without_override(self.src_dicts['properties'])
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
                                elif key == 'dimension':
                                    pass
                                elif key == 'files' :
                                    # files need careful merge
                                    for ikey in favor[key]:
                                        self._process_files_item(ikey, favor)
                                elif key in self.project:
                                    self.project[key] = Project._dict_elim_none(merge_recursive(self.project[key], favor[key]))
        except IOError:
            raise IOError("The module.yaml in project:%s doesn't exist." % self.name)

        self._update_from_src_dict(Project._dict_elim_none(self.src_dicts))
        self.project['type'] = self.project['type'].lower()
        self.project = fix_properties_in_context(self.project, settings.properties)
        
        # always copy portable file to destionation
        self._copy_portable_to_destination()
        self.outdir_path = self._get_output_dir_path(self.tool)
                
        if self.project['type'] != 'exe':
            if self.parent:
                self.parent.update_from_required(self, self.project['type'])
            else:
                raise NameError ("'src' type project %s can't be root project." % (name))
        
        #Process required project
        self.sub_projects = {}
        for subproj in self.project['required']:                        
            if self.project['required'][subproj]:
                merge_without_override(self.project['required'][subproj], project_dicts)
            else:
                self.project['required'][subproj] = project_dicts
            gen.push_properties()
            self.sub_projects[subproj] = Project(subproj, self.tool, self.project['required'][subproj], settings, gen, self)
            gen.pop_properties()
            if self.project['type'] == 'src'and self.sub_projects[subproj].project['type'] != 'src':
                raise NameError ("'src' type project %s required project must be 'src' type, but %s not." % (name, subproj))
            self._inherit_parent_flags_and_macros(self.sub_projects[subproj])
                        
        self.generated_files = {}
    
    def _inherit_parent_flags_and_macros(self, subproj):
        for key in ['common', 'asm', 'c', 'cxx']:
            subproj.project[key] =  Project._dict_elim_none(merge_recursive(self.project[key], subproj.project[key]))
    
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
        
    def update_from_required(self, subproj, ptype):
        """
        update information from sub-src-project  
        """
        if self.project['type'] == 'src':
            self.parent.update_from_required(subproj, ptype)
        
        #Need update for PATH
        src_project = copy.deepcopy(subproj.project)
        
        src_project.pop('required')
        src_project.pop('type')
        if ptype == 'lib':
            src_project.pop('portable')
            src_project['files'].pop("sources")
            if 'TargetOption' in self.project:
                subproj.project['TargetOption'] = self.project['TargetOption']
            
        if ptype != "exe":
            #Merge search path
            if "search_paths" in src_project["linker"]:
                src_project["linker"]["search_paths"] = []
                for path in subproj.project["linker"]["search_paths"]:
                    if os.path.exists(path):
                        src_project["linker"]["search_paths"].append(path)
                    else:
                        src_project["linker"]["search_paths"].append(os.path.join("..", subproj.name, path))
                        
        if ptype == "lib":
            self.project["linker"]["libraries"].append(os.path.basename(subproj.outdir_path))
            self.project["lib_search_paths"].append(os.path.join("..","..", os.path.basename(subproj.outdir_path), self.project['build_dir']))
            if self.tool.startswith('uvision'):
                proj_build_path = os.path.join(*subproj.outdir_path.split(os.sep))
                self.project['files']['sources'].setdefault("Lib", []).append(
                    os.path.join(
                        "..",
                        proj_build_path,
                        self.project['build_dir'],
                        os.path.basename(subproj.outdir_path)+".lib")
                    )
            
        #Merge file path
        if "files" in src_project:
            src_project["files"]["includes"] = {}
            for key, value in subproj.project["files"]["includes"].items():
                src_project["files"]["includes"][key] = []
                for path in value:
                    if os.path.exists(path):
                        src_project["files"]["includes"][key].append(path)
                    else:
                        src_project["files"]["includes"][key].append(os.path.join("..", subproj.name, path))
            if ptype == "src":
                for key, value in subproj.project["files"]["sources"].items():
                    src_project["files"]["sources"][key] = []
                    for path in value:
                        if os.path.exists(path):
                            src_project["files"]["sources"][key].append(path)
                        else:
                            src_project["files"]["sources"][key].append(os.path.join("..", subproj.name, path))
                                                    
        self._update_from_src_dict(src_project, False)
        for dir in subproj.portable_dirs:
            if dir not in self.portable_dirs:
                self.portable_dirs.append(dir)                
    
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
        _list = []
        for item in list_to_clean:
            if item and item not in _list:
                _list.append(item)                
        return _list

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

    def _set_internal_macros_and_flags(self):
        for dest in ['macros', 'flags']:
            for src in ['common', 'c', 'cxx']:                
                self.export[dest][src] = merge_recursive([], self.project[src][dest])                
        self.export['macros'] = Project._dict_elim_none(self.export['macros'])        
        self.export['flags']['ld'] = merge_recursive([], self.project['linker']['flags'])
        self.export['flags'] = Project._dict_elim_none(self.export['flags'])
                
    def _process_include_files(self, files, use_group_name = 'default', add_basepath = True):
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
            # include might be set to None - empty yaml list
            if include_file:
                if not add_basepath:
                    include_file = os.path.normpath(include_file)
                else:
                    include_file = os.path.normpath(os.path.join(self.basepath, include_file))
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

    def _process_source_files(self, files, use_group_name='default', add_basepath = True):
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
            if not add_basepath:
                source_file = os.path.normpath(source_file)
            else:
                source_file = os.path.normpath(os.path.join(self.basepath, source_file))
            if os.path.isdir(source_file):
                self.export['source_paths'].append(source_file)
                self._process_source_files([os.path.join(source_file, f) for f in os.listdir(
                    source_file) if os.path.isfile(os.path.join(source_file, f))], use_group_name, False)

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

    def _get_output_dir_path(self, tool):
        if self.settings.export_location_format != self.settings.DEFAULT_EXPORT_LOCATION_FORMAT:
            location_format = self.settings.export_location_format
        else:
            if 'export_dir' in self.project and self.project['export_dir']:
                location_format = self.project['export_dir']
            else:
                location_format = self.settings.export_location_format

        # substitute all of the different dynamic values
        location = PartialFormatter().format(location_format, **{
            'project_name': self.name,
            'tool': tool,
        })
        return location

    def _get_tool_keywords(self, tool):
        tool_keywords = []
        # get all keywords valid for the tool
        tool_keywords.append(ToolsSupported().get_toolchain(tool))
        tool_keywords += ToolsSupported().get_toolnames(tool)
        tool_keywords = list(set(tool_keywords))
        return tool_keywords
    
    def _fill_export_dict(self, copied=False):

        # Set the template keys an get the relative path to fix all paths
        self.export = get_tool_template()

        location = self._get_output_dir_path(self.tool)
        self.export['output_dir']['path'] = os.path.normpath(location)
        path = self.export['output_dir']['path']
        if copied:
            # Sources were copied, therefore they should be in the exported folder
            self.export['output_dir']['rel_path'] = ''
            self.export['output_dir']['rel_count'] = 0
        else:
            self.export['output_dir']['rel_path'], self.export['output_dir']['rel_count'] = self._generate_output_dir(self.settings, path)

        self._set_internal_files_data()
        self._set_internal_macros_and_flags()
        
        # fixed linker file search path
        for path in self.project['linker']['search_paths']:
            if os.path.exists(path):
                self.export["linker_search_paths"].append(path)
            else:
                self.export["linker_search_paths"].append(os.path.join(self.name, path))
                
        self.export['linker'] = self.project['linker']
        self.export['output_type'] = self.project['type']
        self.export['name'] = self.name
        self.export['type'] = self.project['type']
        self.export['linker_search_paths'].extend(self.project['linker_search_paths'])
        self.export['lib_search_paths'].extend(self.project['lib_search_paths'])
        
        # some tools need special build dir, like uvision
        self.export['build_dir'] = self.project['build_dir']
        self.export['TargetOption'] = self.project['TargetOption']
        try:
            if self.project['type'] == 'exe':
                # some tools only support one linker file,linke uvision
                self.export['linker_file'] = os.path.join(self.name,self.project['linker']['script_files'][0])
        except IndexError:
            raise NameError ("linker file must be set.")
                        
        # re-order include paths
        include_paths = []
        for path in self.export['include_paths']:
            portable = False
            for dir in self.portable_dirs:
                if dir in path:
                    portable = True
            if portable:
                include_paths.insert(0, path)
            else:
                include_paths.append(path)                
        self.export['include_paths'] = include_paths
        
        fix_paths(self.export, self.export['output_dir']['rel_path'],
                   list(FILES_EXTENSIONS.keys()) + ['include_paths', 'source_paths', 'linker_search_paths'])

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
    
    def _ignore_source_files(self, s_cfg_path, d_cfg_path, src, names):
        ignore_names = []
        for name in names:
            if os.path.splitext(name)[1] in [".h", ".hpp", "inc"]:
                d_cfg_file = os.path.normpath(os.path.join(d_cfg_path, os.path.relpath(s_cfg_path, src), name))
                self.project['files']['includes'].setdefault(self._get_portable_group(), []).append(os.path.relpath(d_cfg_file, self.basepath))
            else:
                ignore_names.append(name)                
        return ignore_names
    
    def _ignore_header_files(self, s_port_path, d_port_path, src, names):
        ignore_names = []
        for name in names:
            if os.path.splitext(name)[1] in [".c", ".cpp", "cc"]:
                d_port_file = os.path.normpath(os.path.join(d_port_path, os.path.relpath(s_port_path, src), name))
                self.project['files']['sources'].setdefault(self._get_portable_group(), []).append(os.path.relpath(d_port_file, self.basepath))
            else:
                ignore_names.append(name)
        return ignore_names
    
    def _get_portable_group(self):        
        portable = "%s_%s" % (self.project['portable']['dest'], self.name)
        if self.project['portable']['dest'] not in self.portable_dirs:
            self.portable_dirs.append(self.project['portable']['dest'])
        return portable
        
    def _copy_portable_to_destination(self):
        """ Copies all project portable files to specified project """
        d_cfg_path = os.path.normpath(os.path.join(self.settings.root, self.basepath, "..", self.project['portable']['dest'], "include", self.name))       
        for cfg_key in self.project['portable']['config']:
            d_cfg_path = os.path.normpath(os.path.join(self.settings.root, self.basepath, "..", self.project['portable']['dest'], "include", self.name, cfg_key))
            for cfg in self.project['portable']['config'][cfg_key]:
                s_cfg_path = os.path.normpath(os.path.join(self.settings.root, self.basepath, cfg))
                if os.path.isdir(s_cfg_path):
                    # auto process all header files as config file
                    copytree(s_cfg_path, d_cfg_path,
                                     ignore = lambda src, names: self._ignore_source_files(s_cfg_path, d_cfg_path, src, names))                
                elif os.path.isfile(s_cfg_path):
                    if not os.path.exists(d_cfg_path):
                        os.makedirs(d_cfg_path) 
                    name,ext = os.path.splitext(os.path.basename(s_cfg_path))
                    d_cfg_file = os.path.join(d_cfg_path, name+".h")
                    if not os.path.exists(d_cfg_file):
                        shutil.copy2(s_cfg_path, d_cfg_file)                
                    self.project['files']['includes'].setdefault(self._get_portable_group(), []).append(os.path.relpath(d_cfg_file, self.basepath))
                                    
        for port_key in self.project['portable']['port']:
            d_port_path = os.path.normpath(os.path.join(self.settings.root, self.basepath, "..", self.project['portable']['dest'], "port", self.name, port_key)) 
            for port in self.project['portable']['port'][port_key]:
                port_name, port_ext = os.path.splitext(port)
                if port_ext == ".s":
                    port = port_name + port_ext.upper()
                s_port_path = os.path.normpath(os.path.join(self.settings.root, self.basepath, port))
                if os.path.isdir(s_port_path):
                    copytree(s_port_path, d_port_path,
                                     ignore = lambda src, names: self._ignore_header_files(s_port_path, d_port_path, src, names))
                elif os.path.isfile(s_port_path):
                    if not os.path.exists(d_port_path):
                        os.makedirs(d_port_path) 
                    d_port_file = os.path.join(d_port_path, os.path.basename(s_port_path))
                    if not os.path.exists(d_port_file):
                        shutil.copy2(s_port_path, d_port_file)
                        
                    self.project['files']['sources'].setdefault(self._get_portable_group(), []).append(os.path.relpath(d_port_file, self.basepath))
                
    def clean(self):
        """ Clean a project """

        # We get the export dict formed, then use it for cleaning
        self._fill_export_dict()
        path = self.export['output_dir']['path']

        if os.path.isdir(path):
            logger.info("Cleaning directory %s" % path)

            shutil.rmtree(path)
        return 0

    def generate(self, copied=False, copy=False):
        """ Generates a project """

        generated_files = {}
        result = 0
        exporter = ToolsSupported().get_tool(self.tool)
        
        # None is an error
        if exporter is None:
            result = -1
            logger.debug("Tool: %s was not found" % self.tool)

        self._fill_export_dict(copied)
        if copy:
            logger.debug("Copying sources to the output directory")
            self._copy_sources_to_generated_destination()
        
        # dump a log file if debug is enabled
        if logger.isEnabledFor(logging.DEBUG):
            dump_data = {}
            dump_data['files'] = self.project['files']
            dump_data['tool_specific'] = self.project['tool_specific']
            dump_data['merged'] = self.export
            handler = logging.FileHandler(os.path.join(os.getcwd(), "%s.log" % self.name),"w", encoding=None, delay="true")
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.debug("\n" + yaml.dump(dump_data))

        files = exporter(self.export, self.settings).export_project()
        generated_files[self.tool] = files
        self.generated_files = generated_files
        
        return result

    def build(self):
        """build the project"""

        result = 0
        builder = ToolsSupported().get_tool(self.tool)
        # None is an error
        if builder is None:
            logger.debug("Tool: %s was not found" % builder)
            result = -1

        logger.debug("Building for tool: %s", self.tool)
        logger.debug(self.generated_files)
        if builder(self.generated_files[self.tool], self.settings).build_project() == -1:
            # if one fails, set to -1 to report
            result = -1
        return result

    def get_generated_project_files(self, tool):
        """ Get generated project files, the content depends on a tool. Look at tool implementation """

        exporter = ToolsSupported().get_tool(tool)
        return exporter(self.generated_files[tool], self.settings).get_generated_project_files()

