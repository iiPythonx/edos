# Copyright 2022 iiPython

# Modules
import os
import sys
import atexit
import shutil
import tarfile
import tempfile
from typing import Any, List

# Initialization
open_ = open

# Helper functions
def resolve(p: str) -> str:
    if p[0] == "/":
        result = os.path.join(os.environ["EDOS_DISK"], p[1:])

    else:
        result = os.path.join(os.getcwd(), p)

    path = os.path.abspath(result)
    if os.environ["EDOS_DISK"] not in path:
        return os.environ["EDOS_DISK"]

    return path

def open(p: str, *args, **kwargs) -> Any:
    return open_(resolve(p), *args, **kwargs)

def listdir(p: str = None) -> List[Any]:
    return os.listdir(resolve(p) if p else os.getcwd())

def clean(p: str) -> str:
    return p.replace("\\", "/").replace(os.environ["EDOS_DISK"], "")

def getcwd() -> str:
    return clean(os.getcwd()) or "/"

for f in ["remove"]:
    globals()[f] = lambda p: getattr(os, f)(resolve(p))

for f in ["isfile", "isdir", "islink", "exists"]:
    globals()[f] = lambda p: getattr(os.path, f)(resolve(p))

# Filesystem class
class Filesystem(object):
    def __init__(self, disk_file: str) -> None:
        self.disk_file = disk_file
        self.disk_location = os.path.join(tempfile.gettempdir(), "edos_disk")

        os.environ["EDOS_DISK"] = self.disk_location

        # Handle first-time initialization
        initial_disk_location = os.path.join(os.path.dirname(self.disk_file), "disk")
        if os.path.isdir(initial_disk_location):
            if "--use-disk-folder" in sys.argv:
                self.disk_location = initial_disk_location
                os.environ["EDOS_DISK"] = initial_disk_location

            else:
                self.recompress_disk(initial_disk_location)

        self.decompress_disk()
        atexit.register(self.recompress_disk)

    def decompress_disk(self) -> None:
        if "--use-disk-folder" in sys.argv:
            return

        elif not os.path.isdir(self.disk_location):
            os.mkdir(self.disk_location)

        if os.path.isfile(self.disk_file):
            with tarfile.open(self.disk_file, "r:gz") as disk:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                
                safe_extract(disk, self.disk_location)

    def recompress_disk(self, directory: str = None) -> None:
        if "--use-disk-folder" in sys.argv:
            return

        elif directory is None:
            directory = self.disk_location

        with tarfile.open(self.disk_file, "w:gz") as disk:
            disk.add(directory, "")

        shutil.rmtree(directory)
