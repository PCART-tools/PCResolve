## @package pcresolve.scanner
#  Provide file and directory scanning for Python project source files.
#
#  Contains the FileScanner class for discovering .py and .pyi files in a
#  project directory tree, with filtering for hidden files, __pycache__,
#  and virtual environment directories.

import os
import copy


## Scanner for discovering Python source files in a project directory.
#
#  Walks a directory tree and collects .py/.pyi file paths, with built-in
#  filtering for hidden files, __pycache__, and virtual environment directories.
class FileScanner:
    ## Initialize the scanner.
    def __init__(self):
        self._filePath = []
        self._dirPath = []

    ## Return collected file or directory paths.
    #  @return Deep copy of the collected path list.
    @property
    def path(self):
        return copy.deepcopy(self._filePath)

    ## Return collected directory paths.
    #  @return Deep copy of the collected directory path list.
    @property
    def dirs(self):
        return copy.deepcopy(self._dirPath)

    ## Clear all collected paths so the scanner can be reused.
    def clc(self):
        self._dirPath.clear()
        self._filePath.clear()

    ## Scan the project root directory for Python source files.
    #
    #  @param rootDir The project root directory to scan.
    #  @param py If True, include .py and .pyi files (default: True).
    #  @param pyi If True, include .pyi files (default: True).
    #  @return List of absolute file paths.
    def scan(self, rootDir, py=True, pyi=True):
        self.clc()
        for root, dirs, files in os.walk(rootDir, followlinks=True):
            files = [f for f in files if f[0] != '.']
            dirs[:] = [d for d in dirs if d[0] != '.' and d != '__pycache__' and d != 'include']

            for f in files:
                if f.endswith('.py'):
                    self._filePath.append(os.path.join(root, f))
                elif pyi and f.endswith('.pyi'):
                    self._filePath.append(os.path.join(root, f))

        self._filePath = self._filter_virtualenv_files(self._filePath)
        return self._filePath

    ## Scan for top-level subdirectories only.
    #  @param rootDir The project root directory.
    #  @return List of absolute directory paths.
    def scan_dirs(self, rootDir):
        self.clc()
        for root, dirs, files in os.walk(rootDir, followlinks=True):
            dirs[:] = [d for d in dirs if d[0] != '.' and d != '__pycache__' and d != 'include']
            for d in dirs:
                self._dirPath.append(os.path.join(root, d))
            break
        return self._dirPath

    ## Scan for top-level files only (non-recursive).
    #  @param rootDir The project root directory.
    #  @return List of absolute file paths.
    def scan_files(self, rootDir):
        self.clc()
        for root, dirs, files in os.walk(rootDir, followlinks=True):
            files = [f for f in files if f[0] != '.']
            for f in files:
                if f.endswith('.py') or f.endswith('.pyi'):
                    self._filePath.append(os.path.join(root, f))
            break
        return self._filePath

    ## Filter out files that reside inside virtual environment directories.
    #  @param file_paths List of absolute file paths.
    #  @return Filtered list with virtualenv files removed.
    def _filter_virtualenv_files(self, file_paths):
        virtualenv_dirs = [
            '.venv', 'venv', 'env', 'virtualenv',
            '.env', 'ENV', 'virtualenvironment'
        ]
        filtered = []
        for file_path in file_paths:
            is_virtualenv = False
            for venv_dir in virtualenv_dirs:
                if venv_dir in file_path.split(os.sep):
                    is_virtualenv = True
                    break
            if not is_virtualenv:
                filtered.append(file_path)
        return filtered


## Convenience function to scan a directory and return all Python file paths.
#
#  @param root_dir The project root directory to scan.
#  @param include_pyi Whether to include .pyi stub files (default: True).
#  @return List of absolute file paths.
def scan_directory(root_dir, include_pyi=True):
    scanner = FileScanner()
    return scanner.scan(root_dir, pyi=include_pyi)
