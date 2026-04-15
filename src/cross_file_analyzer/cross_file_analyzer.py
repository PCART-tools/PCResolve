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
                elif isinstance(base,tuple):
                    structured=self._resolve_structured_source(module,base,module_tracers)
                    if structured is not None:
                        _,src_module,src_symbol=structured
                        top_source=self.global_symbols.get(src_module,{}).get(src_symbol,src_symbol)
                    else:
                        top_source=str(base)
                else:
                    if isinstance(base,str) and hasattr(builtins,base):
                        top_source="python"
                    else:
                        top_source=tracer.symbols.get_top(base) or str(base)
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

    def _container_index(self,tracer,container_name,key_idx):
        if not isinstance(key_idx,int):
            return key_idx
        if key_idx>=0:
            return key_idx
        n=tracer.container_lengths.get(container_name)
        if n is not None:
            return key_idx+n
        return key_idx

    def _resolve_container_item(self,module,container_name,key_idx,tracers):
        tracer=tracers.get(module)
        if not tracer:
            return None
        container_idx=self._container_index(tracer,container_name,key_idx)
        item_key=(container_name,container_idx)
        if item_key in tracer.container_items:
            return (module,tracer.container_items[item_key])
        container_direct=tracer.symbols.direct.get(container_name) #跨文件导入
        if self.is_local(container_direct):
            src_module=container_direct
            src_tracer=tracers.get(src_module)
            if not src_tracer:
                return None
            container_idx_src=self._container_index(src_tracer,container_name,key_idx)
            src_key=(container_name,container_idx_src)
            if src_key in src_tracer.container_items:
                return (src_module,src_tracer.container_items[src_key])
        return None

    def _resolve_container_iter(self,module,container_name,tracers):
        tracer=tracers.get(module)
        if not tracer:
            return None
        def to_top_source(src_module,symbol):
            if not symbol:
                return None
            if isinstance(symbol,str) and hasattr(builtins,symbol):
                return "python"
            chain=self.trace_symbol(src_module,symbol,tracers,set())
            if chain:
                return self.extract_final_source(chain)
            src_tracer=tracers.get(src_module)
            if src_tracer:
                top=src_tracer.symbols.get_top(symbol)
                if top:
                    if "." in top:
                        return top.split(".")[0]
                    return top
            if isinstance(symbol,str) and "." in symbol:
                return symbol.split(".")[0]
            return symbol

        def collect_candidates(t, name):
            candidates=[]
            seen=set()
            for (c_name,_),src in t.container_items.items():
                if c_name==name and src:
                    top_src=to_top_source(module if t is tracer else src_module,src)
                    if top_src and top_src not in seen:
                        seen.add(top_src)
                        candidates.append(top_src)
            for src in sorted(t.container_set_sources.get(name,set())):
                if src:
                    top_src=to_top_source(module if t is tracer else src_module,src)
                    if top_src and top_src not in seen:
                        seen.add(top_src)
                        candidates.append(top_src)
            return candidates

        local_candidates=collect_candidates(tracer,container_name)
        if local_candidates:
            return (module,local_candidates)

        container_direct=tracer.symbols.direct.get(container_name)
        if isinstance(container_direct,str) and self.is_local(container_direct):
            src_module=container_direct
            src_tracer=tracers.get(src_module)
            if not src_tracer:
                return None
            src_candidates=collect_candidates(src_tracer,container_name)
            if src_candidates:
                return (src_module,src_candidates)
        return None

    def _resolve_method_symbol(self,module,class_symbol,method_name,tracers,visited):
        tracer=tracers.get(module)
        if not tracer:
            return None
        key=(module,class_symbol,method_name)
        if key in visited:
            return None
        visited.add(key)
        methods=tracer.class_methods.get(class_symbol,[])
        if method_name in methods: #本类
            return (module,method_name)
        for base_symbol in tracer.class_bases.get(class_symbol,[]): #继承父类
            if base_symbol in tracer.class_methods: #父类在同模块定义
                resolved=self._resolve_method_symbol(module,base_symbol,method_name,tracers,visited)
                if resolved:
                    return resolved
            base_direct=tracer.symbols.direct.get(base_symbol)
            if isinstance(base_direct,str):
                if self.is_local(base_direct): #父类从本地模块导入
                    src_module=base_direct
                    resolved=self._resolve_method_symbol(src_module,base_symbol,method_name,tracers,visited)
                    if resolved:
                        return resolved
                else: #父类来自第三方库（复数？）
                    return (module,base_symbol) #父类写成requests.Class2这种（？）
        class_direct=tracer.symbols.direct.get(class_symbol) #本类没有且无父类，跨文件导入类
        if isinstance(class_direct,str):
            if self.is_local(class_direct): #类从本地模块导入
                src_module=class_direct
                resolved=self._resolve_method_symbol(src_module,class_symbol,method_name,tracers,visited)
                if resolved:
                    return resolved
            else: #类来自第三方库
                return (module,class_symbol)
        return None

    def _resolve_structured_source(self,module,direct_source,tracers):
        if not (isinstance(direct_source,tuple) and len(direct_source)==3):
            return None
        kind,a,b=direct_source
        if kind=="container_item": #容器索引
            resolved=self._resolve_container_item(module,a,b,tracers)
            if not resolved:
                return None
            src_module,src_symbol=resolved
            return (f"{a}[{b}]",src_module,src_symbol)
        if kind=="instance_method": #实例方法
            tracer=tracers.get(module)
            if not tracer:
                return None
            class_symbol=tracer.symbols.direct.get(a)
            if not class_symbol:
                return None
            resolved=self._resolve_method_symbol(module,class_symbol,b,tracers,set())
            if not resolved:
                return None
            src_module,src_symbol=resolved
            return (f"{a}.{b}",src_module,src_symbol)
        if kind=="container_iter": #容器迭代
            resolved=self._resolve_container_iter(module,a,tracers)
            if not resolved:
                return None
            src_module,candidates=resolved
            if len(candidates)==1:
                src_symbol=candidates[0]
            else:
                src_symbol="["+",".join(candidates)+"]"
            return (f"{a}[*]",src_module,src_symbol)
        return None

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
        structured=self._resolve_structured_source(module,direct_source,tracers)
        if structured is not None:
            display_name,src_module,src_symbol=structured
            sub_chain=self.trace_symbol(src_module,src_symbol,tracers,visited)
            if sub_chain:
                return [symbol,display_name]+sub_chain
            return [symbol,display_name,src_symbol]
        if isinstance(direct_source,tuple): #未解析成功
            return [symbol,str(direct_source)]
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
            if isinstance(item,str) and hasattr(builtins, item):
                return "python"
            if isinstance(item,str) and not self.is_local(item):
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