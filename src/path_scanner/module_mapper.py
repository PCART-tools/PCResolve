import os
from typing import List
from .getPath import Path

class ModuleMapper:
    """
    文件路径-模块映射器
    """
    def __init__(self, project_root):
        self.project_root=os.path.abspath(project_root)
        self.file_to_module={}
        self.module_to_file={}
        self.path_scanner=Path('DF')
    def scan_project(self):
        """
         扫描项目获取各py与pyi文件路径
        """
        self.path_scanner.getPath(self.project_root)
        py_files=self.path_scanner.path
        py_files=self._filter_virtualenv_files(py_files)
        py_files=[f for f in py_files if f.endswith('.py') or f.endswith('.pyi')]
        for file_path in py_files:
            module_path=self._file_path_to_module_path(file_path)
            if module_path:
                self.file_to_module[file_path]=module_path
                self.module_to_file[module_path]=file_path
        return py_files
    def _filter_virtualenv_files(self,file_paths):
        filtered_files=[]
        virtualenv_dirs=[
            '.venv', 'venv', 'env', 'virtualenv',
            '.env', 'ENV', 'virtualenvironment'
        ]
        for file_path in file_paths:
            is_virtualenv_file=False
            for venv_dir in virtualenv_dirs:
                if venv_dir in file_path.split(os.sep):
                    is_virtualenv_file=True
                    break
            if not is_virtualenv_file:
                filtered_files.append(file_path)
        return filtered_files
    def _file_path_to_module_path(self,file_path):
        """
        文件路径到模块的映射
        """
        try:
            relative_path=os.path.relpath(file_path,self.project_root)
            if relative_path==os.path.basename(file_path):
                module_name=relative_path.replace('.py','').replace('.pyi','')
                return module_name if module_name!='__init__' else ''
            dir_path=os.path.dirname(relative_path)
            file_name=os.path.basename(relative_path)
            module_name=file_name.replace('.py','').replace('.pyi','')
            if module_name=='__init__':
                module_path=dir_path.replace(os.sep,'.')
            else:
                module_path=f"{dir_path.replace(os.sep,'.')}.{module_name}"
            if os.altsep:
                module_path=module_path.replace(os.altsep,'.')
            return module_path
        except Exception as e:
            print(f"转换文件路径时出错{file_path}:{e}")
            return ""
    def get_module_path(self, file_path):
        return self.file_to_module.get(file_path,"")
    def get_file_path(self, module_path):
        return self.module_to_file.get(module_path,"")
    def get_all_modules(self):
        return list(self.module_to_file.keys())
    def get_all_files(self):
        return list(self.file_to_module.keys())
    def print_mapping_summary(self):
        print(f"项目根目录:{self.project_root}")
        print(f"找到{len(self.file_to_module)}个Python文件")
        print("\n相对文件路径->模块路径映射:")
        for file_path,module_path in self.file_to_module.items():
            relative_path=os.path.relpath(file_path, self.project_root)
            print(f"{relative_path}->{module_path}")
    def print_module_paths_only(self):
        modules=sorted(self.get_all_modules())
        for module_path in modules:
            if module_path:
                print(module_path)
    def clear(self):
        self.file_to_module.clear()
        self.module_to_file.clear()
        self.path_scanner.clc()