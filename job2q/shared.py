# -*- coding: utf-8 -*-
import os
import re
from socket import gethostname
from getpass import getuser 
from pwd import getpwnam
from grp import getgrgid
from . import messages
from .readspec import SpecBunch
from .utils import Bunch, removesuffix, p, q
from .fileutils import AbsPath, buildpath
from .readmol import readmol
from .parsing import BoolParser


class ArgList:
    def __init__(self, args):
        self.current = None
        if 'sort' in options.common:
            if options.common.sort == 'natural':
                self.args = sort(args, key=natural)
            elif options.common.sort == 'reverse':
                self.args = sort(args, key=natural, reverse=True)
        else:
            self.args = args
        if 'filter' in options.common:
            self.filter = re.compile(options.common.filter)
        else:
            self.filter = re.compile('.+')
    def __iter__(self):
        return self
    def __next__(self):
        try:
            self.current = self.args.pop(0)
        except IndexError:
            raise StopIteration
        if options.common.base:
            basename = self.current
            rootdir = AbsPath(options.common.root)
        else:
            abspath = AbsPath(self.current, cwd=options.common.root)
            rootdir = abspath.parent()
            filename = abspath.name
            for key in jobspecs.infiles:
                if filename.endswith('.' + key):
                    basename = removesuffix(filename, '.' + key)
                    break
            else:
                messages.failure('La extensión del archivo de entrada', q(filename), 'no está asociada a', jobspecs.packagename)
                return next(self)
            #TODO: Move file checking to AbsPath class
            if not abspath.isfile():
                if not abspath.exists():
                    messages.failure('El archivo de entrada', abspath, 'no existe')
                elif abspath.isdir():
                    messages.failure('El archivo de entrada', abspath, 'es un directorio')
                else:
                    messages.failure('El archivo de entrada', abspath, 'no es un archivo regular')
                return next(self)
        filtermatch = self.filter.fullmatch(basename)
        #TODO: Make filtergroups available to other functions
        if filtermatch:
            filtergroups = filtermatch.groups()
        else:
            return next(self)
        filebools = {key: AbsPath(buildpath(rootdir, (basename, key))).isfile() or key in options.fileopts for key in jobspecs.filekeys}
        for conflict, message in jobspecs.conflicts.items():
            if BoolParser(conflict).evaluate(filebools):
                messages.error(message, p(basename))
                return next(self)
        return rootdir, basename


class OptDict:
    def __init__(self):
        self.__dict__['switch'] = set()
        self.__dict__['define'] = dict()
        self.__dict__['append'] = dict()
    def __setattr__(self, attr, attrval):
        self.__dict__[attr] = attrval
        if isinstance(attrval, Bunch):
            for key, value in attrval.items():
                if value is False:
                    pass
                elif value is True:
                    self.__dict__['switch'].add(key)
                elif isinstance(value, list):
                    self.__dict__['append'].update({key:value})
                else:
                    self.__dict__['define'].update({key:value})
    def interpolate(self):
        if self.common.interpolate:
            if self.common.addmol:
                index = 0
                for path in self.common.addmol:
                    index += 1
                    path = AbsPath(path, cwd=options.common.root)
                    coords = readmol(path)[-1]
                    self.keywords['mol' + str(index)] = '\n'.join('{0:<2s}  {1:10.4f}  {2:10.4f}  {3:10.4f}'.format(*atom) for atom in coords)
                if not 'prefix' in self.common:
                    if len(self.common.addmol) == 1:
                        self.common.prefix = path.stem
                    else:
                        messages.error('Se debe especificar un prefijo cuando se especifican múltiples archivos de coordenadas')
            elif 'allmol' in self.common:
                index = 0
                path = AbsPath(self.common.molall, cwd=options.common.root)
                for coords in readmol(path):
                    index += 1
                    self.keywords['mol' + str(index)] = '\n'.join('{0:<2s}  {1:10.4f}  {2:10.4f}  {3:10.4f}'.format(*atom) for atom in coords)
                prefix.append(path.stem)
                if not 'prefix' in self.common:
                    self.common.prefix = path.stem
            else:
                if not 'prefix' in self.common and not 'suffix' in self.common:
                    messages.error('Se debe especificar un prefijo o un sufijo para interpolar sin archivo coordenadas')
        else:
            if self.keywords or self.common.addmol or 'allmol' in self.common:
                messages.error('Se especificaron variables de interpolación pero no se va a interpolar nada')

names = Bunch()
names.user = getuser()
names.group = getgrgid(getpwnam(getuser()).pw_gid).gr_name
names.host = gethostname()

environ = Bunch()
options = OptDict()
hostspecs = SpecBunch()
jobspecs = SpecBunch()

