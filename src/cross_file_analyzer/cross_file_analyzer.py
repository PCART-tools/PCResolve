import os
import ast
import builtins
from path_scanner.module_mapper import ModuleMapper
from single_file_analyzer.symbol_table_builder import APITracer

class CrossFileAnalyzer:
    def __init__(self, project_root):
        #根目录project_root，模块映射module_mapper
        #全局符号表global_symbols，符号追踪链symbol_chains，API调用all_calls
        self.project_root=project_root
        self.module_mapper=ModuleMapper(project_root)
        self.global_symbols={}
        self.symbol_chains={}
        self.all_calls={}

    def analyze(self):
        self.module_mapper.scan_project()
        all_modules=self.module_mapper.get_all_modules() #all_modules存储所有模块名
        print(f"所有本地模块:{all_modules}")
        print()
        module_tracers={} #module_tracers存储每个模块的tracer实例
        for module in all_modules:
            file_path=self.module_mapper.get_file_path(module)
            if file_path and os.path.exists(file_path):
                with open(file_path,'r',encoding='utf-8') as f:
                    code=f.read()
                tracer=APITracer()
                tree=ast.parse(code)
                tracer.visit(tree)
                module_tracers[module]=tracer
        self.resolve_cross_file_symbols(module_tracers) #跨文件解析一个模块
        self.get_calls(module_tracers) #获取一个模块内的所有api调用

    def is_local(self,module_name):
        if module_name in self.module_mapper.get_all_modules():
            return True
        else:
            return False

    def get_calls(self,module_tracers):
        for module,tracer in module_tracers.items():
            self.all_calls[module]=[]
            for call_detail in tracer.api_calls:
                base=call_detail['base']

                if base in self.global_symbols.get(module,{}):
                    top_source=self.global_symbols[module][base]
                else:
                    if hasattr(builtins,base):
                        top_source="python"
                    else:
                        top_source=tracer.symbols.get_top(base) or base
                call_record={
                    'api':call_detail['api'],
                    'top':top_source
                }
                self.all_calls[module].append(call_record)

    def resolve_cross_file_symbols(self,module_tracers):
        for module,tracer in module_tracers.items():
            self.global_symbols[module]={} #某模块的表
            self.symbol_chains[module]={} #某模块的链
            for symbol,direct_source in tracer.symbols.direct.items():
                chain=self.trace_symbol(module,symbol,module_tracers,set())
                if chain:
                    final_source=self.extract_final_source(chain)
                    self.global_symbols[module][symbol]=final_source #将一个模块某个符号最终来源赋给表
                    self.symbol_chains[module][symbol]=chain #返回一个模块某个符号的链

    def trace_symbol(self,module,symbol,tracers,visited):
        if (module,symbol) in visited:
            return []
        visited.add((module,symbol))
        tracer=tracers.get(module)
        if not tracer:
            return []
        direct_source=tracer.symbols.direct.get(symbol)
        if not direct_source:
            return [symbol]
        #直接来源分支
        if self.is_local(direct_source): #本地模块名
            sub_chain=self.trace_symbol(direct_source,symbol,tracers,visited)
            if sub_chain:
                return [symbol,direct_source]+sub_chain
            else:
                return [symbol,direct_source]

        elif direct_source in tracer.symbols.direct: #本模块里面的符号
            sub_chain=self.trace_symbol(module,direct_source,tracers,visited)
            if sub_chain:
                return [symbol]+sub_chain
            else:
                return [symbol,direct_source]

        else: #第三方库
            return [symbol,direct_source]

    def extract_final_source(self,chain):
        if not chain:
            return ""
        for item in reversed(chain):
            if hasattr(builtins, item):
                return "python"
            if not self.is_local(item):
                if "." in item:
                    return item.split(".")[0]
                return item
        return chain[-1]

    def print_results(self):
        print("全局符号表:")
        for module in sorted(self.global_symbols.keys()):
            print(f"\n{module}模块:")
            for symbol,source in sorted(self.global_symbols[module].items()):
                if source:
                    print(f"{symbol}->{source}")
        print()
        print("全局符号追踪链:")
        for module in sorted(self.symbol_chains.keys()):
            print(f"\n{module}模块:")
            for symbol,chain in sorted(self.symbol_chains[module].items()):
                if chain:
                    chain_str="->".join(chain)
                    print(f"{symbol}:{chain_str}")
        print()
        print("所有调用：")
        for module in sorted(self.all_calls.keys()):
            if self.all_calls[module]:
                print(f"\n{module}模块:")
                for call in self.all_calls[module]:
                    print(f"{call['api']} 的顶层库：{call['top']}")

    def print_all_asts(self):
        all_files=self.module_mapper.get_all_files()
        for file_path in sorted(all_files):
            module_name=self.module_mapper.get_module_path(file_path)
            print(f"\n模块{module_name}:")
            print()
            with open(file_path,'r',encoding='utf-8') as f:
                code=f.read()
            tree=ast.parse(code)
            ast_dump=ast.dump(tree,indent=2)
            print(ast_dump)
            print()