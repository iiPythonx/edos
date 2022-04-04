# Copyright 2022 iiPython

# Modules
import os
import sys
import shlex
import traceback
from magic import from_file
from iipython.iikp import readchar, keys

from edos import fs
from edos.shell.path import PathHandler
from edos.shell.macros import MacroLoader

# Shell class
class Shell(object):
    def __init__(self, root: str) -> None:
        self.root = root

        # Load filesystem
        self.fs = fs.Filesystem(os.path.join(root, "disk.edos"))
        os.chdir(self.fs.disk_location)

        self.path = PathHandler()
        self.macros = MacroLoader().as_dict()

    def autocomplete(self, value: str) -> str:
        value = value.strip("\"")
        if value.startswith("/"):
            path = fs.resolve("/".join(value.split("/")[:-1]) or "/")
            if os.path.isdir(path):
                for file in os.listdir(path):
                    if file.lower().startswith(value.lower().split("/")[-1]):
                        fp = fs.clean(os.path.abspath(os.path.join(path, file)))
                        return fp if " " not in fp else f"\"{fp}\""

    def readline(self, prompt: str) -> str:
        command, last_size = "", 0
        while True:
            prefix = f"{' ' * (last_size + 4)}\r" if len(command) < last_size else ""
            print(f"\r{prefix}{prompt}{command}", end = "")
            last_size = len(command)

            # Handle keypress
            kp = readchar()
            if kp == "\t":
                try:
                    chunks = shlex.split(command, posix = False)

                except ValueError:
                    try:
                        chunks = shlex.split(command + "\"", posix = False)

                    except Exception:
                        chunks = None

                if chunks is not None:
                    chunks[-1] = self.autocomplete(chunks[-1])
                    if chunks[-1] is not None:
                        command = " ".join(chunks)

            elif isinstance(kp, str):
                command += kp

            elif kp == keys.ENTER:
                print()
                return command

            elif kp == keys.CTRL_C:
                raise KeyboardInterrupt

            elif kp == keys.BACKSPACE and command:
                command = command[:-1]

    def handle_input(self) -> None:
        while True:
            command = self.readline(f"{fs.getcwd()} $ ").split(" ")
            cmd, args = command[0], command[1:]

            # Find item on path
            if cmd in self.macros:
                try:
                    self.macros[cmd](self, shlex.split(" ".join(args)))

                except Exception as e:
                    if isinstance(e, ValueError) and "quotation" in str(e):
                        print(f"eDOS Shell: {e}")

                    else:
                        print("Internal macro error:")
                        print(traceback.format_exc())

                continue

            cmd = self.path.resolve(cmd)
            if cmd is None:
                print("eDOS: command not found")
                continue

            # Check how we should run it
            built_command, file_guess = None, from_file(cmd).lower()
            if "python script" in file_guess:
                built_command = f"PYTHONPATH=\"{os.path.join(self.root, 'modules')}\" {sys.executable} {cmd}"

            elif "elf 64-bit lsb executable" in file_guess:
                built_command = cmd

            # Launch file
            if file_guess is None:
                print("File is not an eDOS-compatible executable.")
                continue

            os.system(f"{built_command} {' '.join(args)}")
