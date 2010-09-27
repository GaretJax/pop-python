"""
Fabric commands file to manage the building and deploying of the poplib
package and the related documentation.

@author: Jonathan Stoppani <jonathan.stoppani@edu.hefr.ch>
"""

import os
import urllib
import tarfile
import tempfile
import progressbar
import platform

from fabric.api import local, env, run
from fabric.utils import warn, puts
from fabric.context_managers import cd, show

env.clib_source = "http://gridgroup.hefr.ch/popc/lib/exe/fetch.php/popc-1.3.tgz"
env.clib_prefix = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'popc')


def download_clib(source=None, dest=None):
    if not source:
        source = env.clib_source
    
    class Progress(object):
        def __init__(self, filename):
            self.filename = filename
            self.progress = None
            self.widgets = [
                progressbar.Percentage(), ' ',
                progressbar.Bar(), ' ',
                progressbar.FileTransferSpeed(), ', ',
                progressbar.ETA()
            ]
        
        def __call__(self, count, blocksize, totalsize):
            if not self.progress:
                puts("Downloading {0}".format(self.filename))
                self.progress = progressbar.ProgressBar(widgets=self.widgets, maxval=totalsize).start()
            
            try:
                self.progress.update(count * blocksize)
            except AssertionError:
                self.progress.update(totalsize)
                self.progress.finish()
                puts('')
            
    filename, _ = urllib.urlretrieve(source, filename=dest, reporthook=Progress(source))
    
    return filename


def build_clib(builddir, prefix=None, flags=''):
    if not prefix:
        prefix = env.clib_prefix
    
    with cd(builddir):
        if platform.system() == 'Darwin':
            flags += ' CPPFLAGS=-DARCH_MAC'
        
        puts('\n' + '-'*40)
        local('./configure --prefix={0}{1}'.format(prefix, flags), False)
        
        puts('\n' + '-'*40)
        local('make', False)
        
        puts('\n' + '-'*40)
        local('make install', False)


def install_clib(prefix=None, flags=''):
    if not prefix:
        prefix = env.clib_prefix
    
    puts('')
    
    filename = download_clib()
    dest = tempfile.mkdtemp('-popc')
    
    # Extract sources
    class Filter(object):
        def __init__(self, base, members):
            self.members = members
            self.base = base
            self.valid = []
        
        def valid_members(self):
            for info in self.members:
                # Light sanity check
                if info.name.startswith(('/', '..')):
                    warn("> Ignoring '{0}'! Could affect other paths outside the untar directory.".format(info.name))
                else:
                    puts(info.name)
                    self.valid.append(info.name)
                    yield info
        
        def prefix(self):
            prefix = os.path.join(self.base, os.path.commonprefix(self.valid))
            
            if not os.path.isdir(prefix):
                prefix = os.path.split(prefix)[0]
            
            return prefix
    
    puts("Unpacking {0}".format(filename))
    puts("       to {0}".format(dest))
    tarball = tarfile.open(filename)
    f = Filter(dest, tarball)
    tarball.extractall(dest, f.valid_members())
    
    # Configure
    build_clib(f.prefix(), prefix, flags)
    
    # Cleanup
    puts("Removing {0}".format(filename))
    os.remove(filename)
    
    puts("Removing {0}".format(dest))
    for root, dirs, files in os.walk(dest, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))






