# Copyright 2014-2015 0xc0170
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
import yaml
import locale
import shutil
import string
import operator
import copy
import re

from functools import reduce

FILES_EXTENSIONS = {
    'include_files': ['h', 'hpp', 'inc'],
    'source_files_s': ['s'],
    'source_files_c': ['c'],
    'source_files_cpp': ['cpp', 'cc'],
    'source_files_lib': ['lib', 'ar', 'a'],
    'source_files_obj': ['o', 'obj'],
    'linker_file': ['sct', 'ld', 'lin', 'icf'],
}

FILE_MAP = {v:k for k,values in FILES_EXTENSIONS.items() for v in values}
SOURCE_KEYS = ['source_files_c', 'source_files_s', 'source_files_cpp', 'source_files_lib', 'source_files_obj']
VALID_EXTENSIONS = reduce(lambda x,y:x+y,[FILES_EXTENSIONS[key] for key in SOURCE_KEYS])

def rmtree_if_exists(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)

def uniqify(_list):
    # see: http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order/29898968#29898968
    return reduce(lambda r, v: v in r[1] and r or (r[0].append(v) or r[1].add(v)) or r, _list, ([], set()))[0]

def merge_recursive(*args):
    if all(isinstance(x, dict) for x in args):
        output = {}
        keys = reduce(operator.or_, [set(x) for x in args])

        for key in keys:
            # merge all of the ones that have them
            output[key] = merge_recursive(*[x[key] for x in args if key in x])

        return output
    else:
        if len(args) == 1 or (len(args) > 1 and args[1] is None):
            return args[0]
        elif (len(args) > 1 and args[0] is None):
            return args[1]
        elif type(args[0]) is str:
            return args[0]
        elif type(args[0]) is dict and type(args[1]) is list:
            _args = [args[0], {"": args[1]}]
            return merge_recursive(*_args)
        else:
            return reduce(operator.add, args)
    
def merge_without_override(dest, src):
    """
    process list as a single object.
    """
    for key, value in src.items():
        if type(value) is dict:
            if key in dest:
                merge_without_override(dest[key], value)
            else:
                dest[key] = copy.deepcopy(value)
        else:
            if key not in dest:
                dest[key] = copy.deepcopy(value)
            else:
                pass
            
def merge_with_override(dest, src):
    """
    process list as a single object.
    """
    for key, value in src.items():
        if type(value) is dict:
            if key in dest:
                merge_with_override(dest[key], value)
            else:
                dest[key] = copy.deepcopy(value)
        else:
            dest[key] = copy.deepcopy(value)
            
def flatten(S):
    if S == []:
        return S
    if isinstance(S[0], list):
        return flatten(S[0]) + flatten(S[1:])
    return S[:1] + flatten(S[1:])

class PartialFormatter(string.Formatter):
    def get_field(self, field_name, args, kwargs):
        try:
            val = super(PartialFormatter, self).get_field(field_name, args, kwargs)
        except (IndexError, KeyError, AttributeError):
            first, _ = field_name._formatter_field_name_split()
            val = '{' + field_name + '}', first
        return val
    
def fix_properties_in_context(dest, prop):
    def userVar_sub(matchobj):
        name = matchobj.group(1)
        tag = ""
        if '#' in name:
            name, tag = name.split("#")
            
        if name in prop:
            ans = prop[name]
            if type(ans) != str:
                raise SystemError("Found property:%s is list type." % name)
            elif tag:
                return ans.__getattribute__(tag)()
            else:
                return ans
        else :
            raise SystemError("Found property:%s can be resolved." % name)
    
    if type(dest) == dict:
        ndest = {}
        for k,v in dest.items():
            ndest[k] = fix_properties_in_context(v, prop)
        return ndest
    elif type(dest) == list:
        ndest = []
        for v in dest:
            ndest.append(fix_properties_in_context(v, prop))
        return ndest
    elif type(dest) == str:
        return re.sub(r'\${(.*?)}', userVar_sub, dest)
    else:
        return dest

def fix_paths(project_data, rel_path, extensions):
    """ Fix paths for extension list """
    norm_func = lambda path : os.path.normpath(os.path.join(rel_path, path))
    for key in extensions:
        if key in project_data:
            if type(project_data[key]) is dict:
                for k,v in project_data[key].items():
                    project_data[key][k] = [norm_func(i) for i in v]
            elif type(project_data[key]) is list:
                project_data[key] = [norm_func(i) for i in project_data[key]]
            else:
                project_data[key] = norm_func(project_data[key])

def fix_path(rel_path, path):
    ''' fixed single path '''
    return os.path.normpath(os.path.join(rel_path, path))


def copytree(src, dst, ignore = None):
    '''Copy without override'''
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()
    if not os.path.exists(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        
        try:
            if os.path.isdir(srcname):
                copytree(srcname, dstname, ignore)
            elif not os.path.exists(dstname):
                shutil.copy2(srcname, dstname)
        except shutil.Error, err:
            errors.extend(err.args[0])
        except EnvironmentError, why:
            errors.append((srcname, dstname, str(why)))
            
    try:
        shutil.copystat(src, dst)
    except OSError, why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.append((src, dst, str(why)))
    if errors:
        raise shutil.Error, errors
