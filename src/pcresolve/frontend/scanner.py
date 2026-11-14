## @package pcresolve.frontend.scanner
#  Provide file and directory scanning for Python project source files.
#
#  Contains the FileScanner class for discovering .py and .pyi files in a
#  project directory tree, with filtering for hidden files, __pycache__,
#  and virtual environment directories.
#  扫描项目中的 Python 源文件，并过滤隐藏目录、缓存和虚拟环境。

import os
import copy


## Scanner for discovering Python source files in a project directory.
## 在项目目录中发现 Python 源文件的扫描器。
#
#  Walks a directory tree and collects .py/.pyi file paths, with built-in
#  filtering for hidden files, __pycache__, and virtual environment directories.
class FileScanner:
    ## Initialize the scanner.
    ## 初始化已收集文件和目录的状态。
    #
    #  @return None
    def __init__(self):
        self._filePath = []
        self._dirPath = []

    ## Return collected file or directory paths.
    ## 返回已收集的文件路径。
    #
    #  @return Deep copy of the collected path list.
    @property
    def path(self):
        return copy.deepcopy(self._filePath)

    ## Return collected directory paths.
    ## 返回已收集的目录路径。
    #
    #  @return Deep copy of the collected directory path list.
    @property
    def dirs(self):
        return copy.deepcopy(self._dirPath)

    ## Clear all collected paths so the scanner can be reused.
    ## 清空已收集的路径，以便复用扫描器。
    #
    #  @return None
    def clc(self):
        self._dirPath.clear()
        self._filePath.clear()

    ## Scan the project root directory for Python source files.
    ## 递归扫描项目根目录中的 Python 源文件。
    #
    #  @param rootDir The project root directory to scan.
    #  @param py Retained for compatibility; .py files are always included.
    #  @param pyi If True, include .pyi files (default: True).
    #  @return Discovered file paths, rooted at the supplied directory.
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

        # Filter by path component after traversal so nested environments are excluded.
        # 遍历后按路径分量过滤，排除嵌套的虚拟环境。
        self._filePath = self._filter_virtualenv_files(self._filePath)
        return self._filePath

    ## Scan for top-level subdirectories only.
    ## 仅扫描根目录下的直接子目录。
    #
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
    ## 仅扫描根目录下的 Python 文件，不递归进入子目录。
    #
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
    ## 排除位于虚拟环境目录中的文件。
    #
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
## 扫描目录并返回发现的 Python 文件路径。
#
#  @param root_dir The project root directory to scan.
#  @param include_pyi Whether to include .pyi stub files (default: True).
#  @return List of absolute file paths.
def scan_directory(root_dir, include_pyi=True):
    scanner = FileScanner()
    return scanner.scan(root_dir, pyi=include_pyi)
