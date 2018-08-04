# Copyright 2017-2020
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

import copy
import logging

from collections import OrderedDict
# eclipse works with linux paths
from os.path import normpath, join, basename

from .tool import Tool, Builder, Exporter
from .gccarm import MakefileGccArm
from ..util import SOURCE_KEYS

logger = logging.getLogger('progen.tools.gnu_mcu_eclipse')

class EclipseGnuMCU(Tool, Exporter, Builder):

    file_types = {'cpp': 1, 'c': 1, 's': 1, 'obj': 1, 'lib': 1, 'h': 1}

    generated_project = {
        'path': '',
        'files': {
            'proj_file': '',
            'cproj': ''
        }
    }
    
    #GNU MCU Plugin ID
    MFPU_COMMAND2ID = {
        "default":"default",
        "-mfpu=crypto-neon-fp-armv8":"cryptoneonfparmv8",
        "-mfpu=fpa":"fpa",
        "-mfpu=fpe2":"fpe2",
        "-mfpu=fpe3":"fpe3",
        "-mfpu=fp-armv8":"fparmv8",
        "-mfpu=fpv4-sp-d16":"fpv4spd16",
        "-mfpu=fpv5-d16":"fpv5d16",
        "-mfpu=fpv5-sp-d16":"fpv5spd16",
        "-mfpu=maverick":"maverick",
        "-mfpu=neon":"neon",
        "-mfpu=neon-fp16":"neonfp16",
        "-mfpu=neon-fp-armv8":"neonfparmv8",
        "-mfpu=neon-vfpv4":"neonvfpv4",
        "-mfpu=vfp":"vfp",
        "-mfpu=vfpv3":"vfpv3",
        "-mfpu=vfpv3-d16":"vfpv3d16",
        "-mfpu=vfpv3-d16-fp16":"vfpv3d16fp16",
        "-mfpu=vfpv3-fp16":"vfpv3fp16",
        "-mfpu=vfpv3xd":"vfpv3xd",
        "-mfpu=vfpv3xd-fp16":"vfpv3xdfp16",
        "-mfpu=vfpv4":"vfpv4",
        "-mfpu=vfpv4-d16":"vfpv4d16"
    }
    
    @staticmethod
    def get_mfpu_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.MFPU_COMMAND2ID:
            trip_cmd = "default"
        return EclipseGnuMCU.MFPU_COMMAND2ID[trip_cmd]
    
    FPUABI_COMMAND2ID = { 
        "":"default",
        "-mfloat-abi=soft":"soft",
        "-mfloat-abi=softfp":"softfp",
        "-mfloat-abi=hard":"hard"
    }
    
    @staticmethod
    def get_fpuabi_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.FPUABI_COMMAND2ID:
            trip_cmd = ""
        return EclipseGnuMCU.FPUABI_COMMAND2ID[trip_cmd]
    
    MCPU_COMMAND2ID = {
        "-mcpu=arm1020e":"arm1020e",
        "-mcpu=arm1020t":"arm1020t",
        "-mcpu=arm1022e":"arm1022e",
        "-mcpu=arm1026ej-s":"arm1026ej-s",
        "-mcpu=arm10e":"arm10e",
        "-mcpu=arm10tdmi":"arm10tdmi",
        "-mcpu=arm1136j-s":"arm1136j-s",
        "-mcpu=arm1136jf-s":"arm1136jf-s",
        "-mcpu=arm1156t2-s":"arm1156t2-s",
        "-mcpu=arm1156t2f-s":"arm1156t2f-s",
        "-mcpu=arm1176jz-s":"arm1176jz-s",
        "-mcpu=arm1176jzf-s":"arm1176jzf-s",
        "-mcpu=arm2":"arm2",
        "-mcpu=arm250":"arm250",
        "-mcpu=arm3":"arm3",
        "-mcpu=arm6":"arm6",
        "-mcpu=arm60":"arm60",
        "-mcpu=arm600":"arm600",
        "-mcpu=arm610":"arm610",
        "-mcpu=arm620":"arm620",
        "-mcpu=arm7":"arm7",
        "-mcpu=arm70":"arm70",
        "-mcpu=arm700":"arm700",
        "-mcpu=arm700i":"arm700i",
        "-mcpu=arm710":"arm710",
        "-mcpu=arm7100":"arm7100",
        "-mcpu=arm710c":"arm710c",
        "-mcpu=arm710t":"arm710t",
        "-mcpu=arm720":"arm720",
        "-mcpu=arm720t":"arm720t",
        "-mcpu=arm740t":"arm740t",
        "-mcpu=arm7500":"arm7500",
        "-mcpu=arm7500fe":"arm7500fe",
        "-mcpu=arm7d":"arm7d",
        "-mcpu=arm7di":"arm7di",
        "-mcpu=arm7dm":"arm7dm",
        "-mcpu=arm7dmi":"arm7dmi",
        "-mcpu=arm7m":"arm7m",
        "-mcpu=arm7tdmi":"arm7tdmi",
        "-mcpu=arm7tdmi-s":"arm7tdmi-s",
        "-mcpu=arm8":"arm8",
        "-mcpu=arm810":"arm810",
        "-mcpu=arm9":"arm9",
        "-mcpu=arm920":"arm920",
        "-mcpu=arm920t":"arm920t",
        "-mcpu=arm922t":"arm922t",
        "-mcpu=arm926ej-s":"arm926ej-s",
        "-mcpu=arm940t":"arm940t",
        "-mcpu=arm946e-s":"arm946e-s",
        "-mcpu=arm966e-s":"arm966e-s",
        "-mcpu=arm968e-s":"arm968e-s",
        "-mcpu=arm9e":"arm9e",
        "-mcpu=arm9tdmi":"arm9tdmi",
        "-mcpu=cortex-a12":"cortex-a12",
        "-mcpu=cortex-a15":"cortex-a15",
        "-mcpu=cortex-a17":"cortex-a17",
        "-mcpu=cortex-a32":"cortex-a32",
        "-mcpu=cortex-a35":"cortex-a35",
        "-mcpu=cortex-a5":"cortex-a5",
        "-mcpu=cortex-a53":"cortex-a53",
        "-mcpu=cortex-a57":"cortex-a57",
        "-mcpu=cortex-a7":"cortex-a7",
        "-mcpu=cortex-a72":"cortex-a72",
        "-mcpu=cortex-a8":"cortex-a8",
        "-mcpu=cortex-a9":"cortex-a9",
        "-mcpu=cortex-m0":"cortex-m0",
        "-mcpu=cortex-m0.small-multiply":"cortex-m0-small-multiply",
        "-mcpu=cortex-m0plus":"cortex-m0plus",
        "-mcpu=cortex-m0plus.small-multiply":"cortex-m0plus-small-multiply",
        "-mcpu=cortex-m1":"cortex-m1",
        "-mcpu=cortex-m1.small-multiply":"cortex-m1-small-multiply",
        "-mcpu=cortex-m23":"cortex-m23",
        # default          
        "-mcpu=cortex-m3":"cortex-m3",
        "-mcpu=cortex-m33":"cortex-m33",
        "-mcpu=cortex-m4":"cortex-m4",
        "-mcpu=cortex-m7":"cortex-m7",
        "-mcpu=cortex-r4":"cortex-r4",
        "-mcpu=cortex-r4f":"cortex-r4f",
        "-mcpu=cortex-r5":"cortex-r5",
        "-mcpu=cortex-r7":"cortex-r7",
        "-mcpu=cortex-r8":"cortex-r8",
        "-mcpu=ep9312":"ep9312",
        "-mcpu=exynos-m1":"exynos-m1",
        "-mcpu=fa526":"fa526",
        "-mcpu=fa606te":"fa606te",
        "-mcpu=fa626":"fa626",
        "-mcpu=fa626te":"fa626te",
        "-mcpu=fa726te":"fa726te",
        "-mcpu=fmp626":"fmp626",
        "-mcpu=generic-armv7-a":"generic-armv7-a",
        "-mcpu=iwmmxt":"iwmmxt",
        "-mcpu=iwmmxt2":"iwmmxt2"
    }
    
    @staticmethod
    def get_mcpu_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.MCPU_COMMAND2ID:
            trip_cmd = "-mcpu=cortex-m3"
        return EclipseGnuMCU.MCPU_COMMAND2ID[trip_cmd]
    
    OPTIMIZATIONLEVEL_COMMAND2ID = { 
        "-O0":"none",
        "-O1":"optimize",
        "-O2":"more",
        "-O3":"most",
        "-Os":"size",
        "-Og":"debug",
    }
    
    @staticmethod
    def get_optimization_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.OPTIMIZATIONLEVEL_COMMAND2ID:
            trip_cmd = "-O2"
        return EclipseGnuMCU.OPTIMIZATIONLEVEL_COMMAND2ID[trip_cmd]
    
    DEBUGLEVEL_COMMAND2ID = { 
        "default":"none",
        "-g1":"minimal",
        "-g":"default",
        "-g3":"max"
    }
    
    @staticmethod
    def get_debug_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.DEBUGLEVEL_COMMAND2ID:
            trip_cmd = "default"
        return EclipseGnuMCU.DEBUGLEVEL_COMMAND2ID[trip_cmd]
    
    INSTRUCTIONSET_COMMAND2ID = { 
        "":"default",
        "-mthumb":"thumb",
        "-marm":"arm"
    }
    
    @staticmethod
    def get_instructionset_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.INSTRUCTIONSET_COMMAND2ID:
            trip_cmd = ""
        return EclipseGnuMCU.INSTRUCTIONSET_COMMAND2ID[trip_cmd]
    
    UNALIGNEDACCESS_COMMAND2ID = { 
        "":"default",
        "-munaligned-access":"enabled",
        "-mno-unaligned-access":"disabled"
    }
    
    @staticmethod
    def get_unalignedaccess_gnuarmeclipse_id(command):
        trip_cmd = command.strip().lower()
        if trip_cmd not in EclipseGnuMCU.UNALIGNEDACCESS_COMMAND2ID:
            trip_cmd = ""
        return EclipseGnuMCU.UNALIGNEDACCESS_COMMAND2ID[trip_cmd]
    
    # all bool gnu mcu eclipse options store here
    GNU_MCU_BOOL_COMMAND2OPTIONS = {
        "-fmessage-length=0":"false",
        "-fsigned-char":"false",
        "-ffunction-sections":"false",
        "-fdata-sections":"false",
        "-fno-common":"false",
        "-Wall":"false",
        "-Wextra":"false",
        "-Wlogical-op":"false",
        "-Wagreggate-return":"false",
        "-Wfloat-equal":"false",
        "-Wabi":"false",
        "-fno-exceptions":"false",
        "-fno-rtti":"false",
        "-fno-use-cxa-atexit":"false",
        "-fno-threadsafe-statics":"false",
        "-Xlinker --gc-sections":"false"
        }
    
    #Other debug flags, Other Warning flag, Other Optimization flag
            
    def __init__(self, workspace, env_settings):
        self.definitions = 0
        self.exporter = MakefileGccArm(workspace, env_settings)
        self.workspace = workspace
        self.env_settings = env_settings
    
    @staticmethod
    def get_toolnames():
        return ['gnu_mcu_eclipse']

    @staticmethod
    def get_toolchain():
        return 'gcc_arm'

    def _expand_one_file(self, source, new_data, extension):
        # use reference count to instead '..'
        source = normpath(source).replace('../', '').replace('..\\', '')
        return {"path": join('PARENT-%s-PROJECT_LOC' % new_data['output_dir']['rel_count'], source).replace('\\', '/'),
                "name": basename(source), 
                "type": self.file_types[extension.lower()]}

    def _expand_sort_key(self, file) :
        return file['name'].lower()

    def export_workspace(self):
        logger.debug("Current version of CoIDE does not support workspaces")

    def export_project(self):
        """ Processes groups and misc options specific for eclipse, and run generator """

        output = copy.deepcopy(self.generated_project)
        data_for_gnu_mcu = self.workspace.copy()

        self.exporter.process_data_for_makefile(data_for_gnu_mcu)   

        # process path format in windows
        for name in ['linker_file','toolchain_bin_path',
                     'lib_paths', 'include_paths', 'source_paths',
                     'source_files_c', 'source_files_cpp', 'source_files_s']:
            if type(data_for_gnu_mcu[name]) == list:
                new_paths = []
                for path in data_for_gnu_mcu[name]:
                    new_paths.append(path.replace('\\', '/'))
                data_for_gnu_mcu[name] = new_paths
            elif data_for_gnu_mcu[name]:
                data_for_gnu_mcu[name] = data_for_gnu_mcu[name].replace('\\', '/')

        expanded_dic = self.workspace.copy()
        expanded_dic['rel_path'] = data_for_gnu_mcu['output_dir']['rel_path']
        groups = self._get_groups(expanded_dic)
        expanded_dic['groups'] = {}
        for group in groups:
            expanded_dic['groups'][group] = []
        self._iterate(self.workspace, expanded_dic)

        expanded_dic["options"] = {}
        expanded_dic["options"]["optimization"] = EclipseGnuMCU.get_optimization_gnuarmeclipse_id("")
        expanded_dic["options"]["debug"] = EclipseGnuMCU.get_debug_gnuarmeclipse_id("")
        expanded_dic["options"]["mcu"] = EclipseGnuMCU.get_mcpu_gnuarmeclipse_id("")
        expanded_dic["options"]["instructionset"] = EclipseGnuMCU.get_instructionset_gnuarmeclipse_id("")
        expanded_dic["options"]["fpuabi"] = EclipseGnuMCU.get_fpuabi_gnuarmeclipse_id("")
        expanded_dic["options"]["fpu"] = EclipseGnuMCU.get_mfpu_gnuarmeclipse_id("")
        expanded_dic["options"]["unalignedaccess"] = EclipseGnuMCU.get_unalignedaccess_gnuarmeclipse_id("")
        
        for name in ["common_flags", "ld_flags", "c_flags", "cxx_flags", "asm_flags"] :
            for flag in data_for_gnu_mcu[name] :
                if flag.startswith("-O") :
                    expanded_dic["options"]["optimization"] = EclipseGnuMCU.get_optimization_gnuarmeclipse_id(flag)
                elif flag.startswith("-g") :
                    expanded_dic["options"]["optimization"] = EclipseGnuMCU.get_debug_gnuarmeclipse_id(flag)
                elif flag.startswith("-mcpu=") :
                    expanded_dic["options"]["mcu"] = EclipseGnuMCU.get_mcpu_gnuarmeclipse_id(flag)
                elif flag in ["-mthumb", "-marm"] :
                    expanded_dic["options"]["mcu"] = EclipseGnuMCU.get_instructionset_gnuarmeclipse_id(flag)
                elif flag.starswith("-mfloat-abi=") :
                    expanded_dic["options"]["fpuabi"] = EclipseGnuMCU.get_fpuabi_gnuarmeclipse_id(flag)
                elif flag.starswith("-mfpu=") :
                    expanded_dic["options"]["fpu"] = EclipseGnuMCU.get_mfpu_gnuarmeclipse_id(flag)
                elif flag in ["-munaligned-access","-mno-unaligned-access"]:
                    expanded_dic["options"]["unalignedaccess"] = EclipseGnuMCU.get_unalignedaccess_gnuarmeclipse_id(flag)
                elif flag in EclipseGnuMCU.GNU_MCU_BOOL_COMMAND2OPTIONS:
                    EclipseGnuMCU.GNU_MCU_BOOL_COMMAND2OPTIONS[flag] = "true"
                else:
                    # TODO process others flags
                    pass
                            
        expanded_dic["options"]["value"] = EclipseGnuMCU.GNU_MCU_BOOL_COMMAND2OPTIONS
        
        # Project file
        project_path, output['files']['cproj'] = self.gen_file_jinja(
            'gnu_mcu_eclipse.cproject.tmpl', expanded_dic, '.cproject', data_for_gnu_mcu['output_dir']['path'])

        project_path, output['files']['proj_file'] = self.gen_file_jinja(
            'eclipse.project.tmpl', expanded_dic, '.project', data_for_gnu_mcu['output_dir']['path'])
        return output

    def get_generated_project_files(self):
        return {'path': self.workspace['path'], 'files': [self.workspace['files']['proj_file'], self.workspace['files']['cproj'],
            self.workspace['files']['makefile']]}

