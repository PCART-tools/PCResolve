import  ast

class TracingTop:
    """
    追踪顶层库
    """
    def __init__(self):
        self.direct={}
        self.top={}
        self.chains={}

    def trace(self,symbol,visited=None):
        if visited is None:
            visited=set()
        if symbol in visited:
            return []
        visited.add(symbol)
        if symbol not in self.direct:
            return [symbol]
        source=self.direct[symbol]
        subchain=self.trace(source,visited)
        return [symbol]+subchain

    def get_top(self,symbol):
        if symbol in self.top:
            return self.top[symbol]
        chain=self.trace(symbol)
        if chain:
            self.top[symbol]=chain[-1]
            return chain[-1]
        return None

    def get_chain(self,symbol):
        return self.chains.get(symbol, [])

    def add(self,symbol,source):
        if not symbol or not source:
            return
        print(f"添加符号：{symbol}->{source}")
        self.direct[symbol]=source
        chain=self.trace(symbol)
        self.chains[symbol]=chain
        if chain:
            self.top[symbol]=chain[-1]
            print(f"符号链:{'->'.join(map(str,chain))}")

class APITracer(ast.NodeVisitor):
    """
    单文件追踪器
    """
    def __init__(self):
        self.symbols=TracingTop()
        self.api_calls=[]
        self.attr_accesses=[]
        self.local=set()
        self._func_stack=[]
        self.function_call_tops={}
        self.container_items={}
        self.container_lengths={}
        self.container_set_sources={}
        self.class_methods={}
        self.class_bases={}
        self.import_from_symbols={}

    def visit_Import(self,node):
        for alias in node.names:
            symbol=alias.asname if alias.asname else alias.name
            self.symbols.add(symbol,alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self,node):
        for alias in node.names:
            symbol=alias.asname if alias.asname else alias.name
            self.symbols.add(symbol,node.module)
            self.import_from_symbols[symbol]=node.module
        self.generic_visit(node)

    def trace_source(self,node):
        if isinstance(node,ast.Name):
            return node.id
        elif isinstance(node,ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0])
            me=self._resolve_methods(node)
            if me:
                return me
            call_key=self.get_base(node,call_lookup=True) #打开
            if call_key:
                return call_key
            return self.get_base(node.func)
        elif isinstance(node,ast.Attribute):
            return self.get_base(node)
        elif isinstance(node,ast.Lambda):
            return self.get_base(node.body)
        elif isinstance(node,ast.Subscript):
            container_name=self.get_base(node.value)
            key_idx=self._get_slice(node.slice)
            if container_name is not None and key_idx is not None:
                key_value=self._container_index(container_name,key_idx)
                lookup_key=(container_name,key_value)
                if lookup_key in self.container_items:
                    return self.container_items[lookup_key]
                return ("container_item",container_name,key_idx) #不在本地
            return container_name     
        elif isinstance(node,(ast.Dict,ast.List,ast.Tuple,ast.Set)):
            if isinstance(node,ast.Dict):
                value_nodes=node.values
            else:
                value_nodes=node.elts
            bases=set()
            for v in value_nodes:
                base=self.get_base(v)
                if base:
                    bases.add(base)
            if len(bases)==1:
                return next(iter(bases))
            return None
        elif isinstance(node,ast.Constant):
            return str(node.value)
        return None

    def _is_partial_call(self,node):
        if not isinstance(node, ast.Call):
            return False
        func=node.func
        if isinstance(func,ast.Name) and func.id=='partial':
            return True
        if isinstance(func,ast.Attribute) and func.attr=='partial':
            return True
        return False

    def _get_slice(self,slice_node):
        if isinstance(slice_node,ast.Constant):
            return slice_node.value
        if isinstance(slice_node,ast.UnaryOp) and isinstance(slice_node.op,ast.USub) and isinstance(slice_node.operand,ast.Constant):
            return -slice_node.operand.value
        return None

    def _container_index(self,container_name,idx):
        if not isinstance(idx,int):
            return idx
        if idx>=0:
            return idx
        n=self.container_lengths.get(container_name)
        if n:
            return idx+n
        return idx

    def _resolve_methods(self,node):
        if not isinstance(node,ast.Call):
            return None
        func=node.func
        if not isinstance(func,ast.Attribute):
            return None
        re=func.value
        if not isinstance(re,ast.Name):
            return None
        method_name=func.attr
        class_name=self.symbols.direct.get(re.id)
        if not class_name:
            return None
        methods=self.class_methods.get(class_name)
        if methods and method_name in methods:
            return method_name
        if class_name in self.class_methods or class_name in self.import_from_symbols: #本地或导入
            return ("instance_method",re.id,method_name)
        return None

    def _attribute_chain_list(self,node):
        parts=[]
        remain=node
        while isinstance(remain,ast.Attribute):
            parts.append(remain.attr)
            remain=remain.value
        if isinstance(remain,ast.Name):
            parts.append(remain.id)
            return list(reversed(parts))
        return None

    def _attribute_name(self,node): #属性名
        chain=self._attribute_chain_list(node)
        if chain:
            return ".".join(chain)
        return None

    def _decorator_source(self,deco_node): #装饰器来源
        return self.trace_source(deco_node)

    def _bind_decorated_target(self,target_name,deco_source):
        if not deco_source:
            return
        if isinstance(deco_source,str) and deco_source in self.function_call_tops:
            for top in sorted(self.function_call_tops[deco_source]):
                if top and top not in ("local","python"):
                    self.symbols.add(target_name,top)
                    return
        deco_top=self.symbols.get_top(deco_source)
        if deco_top:
            self.symbols.add(target_name,deco_top)
        else:
            self.symbols.add(target_name,deco_source)

    def _bind_target_to_source(self,target,source):
        if not source:
            return
        if isinstance(target,ast.Name):
            self.symbols.add(target.id,source)
            return
        if isinstance(target,ast.Attribute):
            name=self._attribute_name(target)
            if name and name.startswith("self."):
                self.symbols.add(name,source)
            return
        if isinstance(target,(ast.Tuple,ast.List)):
            for elt in target.elts:
                self._bind_target_to_source(elt,source)

    def _iter_source(self,iter_node):
        if isinstance(iter_node,ast.Name):
            container_name=iter_node.id
            has_items=any(k[0]==container_name for k in self.container_items.keys())
            has_set=container_name in self.container_set_sources
            if has_items or has_set:
                return ("container_iter",container_name,"*")
        source=self.trace_source(iter_node)
        if source:
            return source
        return self.get_base(iter_node)

    def get_base(self,node,call_lookup=False): #默认不解析，只取根
        if isinstance(node,ast.Name):
            return node.id
        elif isinstance(node,ast.Attribute):
            chain=self._attribute_chain_list(node)
            if chain:
                return chain[0]
        elif isinstance(node,ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0],call_lookup=call_lookup)
            if call_lookup: #解析接收者
                func=node.func
                if isinstance(func,ast.Attribute):
                    return self._attribute_name(func.value)
                if isinstance(func,ast.Name):
                    return func.id
                return None
            return self.get_base(node.func,call_lookup=False)
        elif isinstance(node,ast.Lambda):
            return self.get_base(node.body,call_lookup=call_lookup)
        return None

    def visit_Assign(self,node):
        if isinstance(node.value,ast.Dict): #字典
            for target in node.targets:
                if isinstance(target,ast.Name):
                    container_name=target.id
                    for key_node,value_node in zip(node.value.keys,node.value.values):
                        if isinstance(key_node,ast.Constant):
                            key_value=key_node.value
                            value_source=self.get_base(value_node)
                            if value_source:
                                self.container_items[(container_name,key_value)]=value_source
        if isinstance(node.value,(ast.List,ast.Tuple)): #列表或元组,跨文件处理
            for target in node.targets:
                if isinstance(target,ast.Name):
                    container_name=target.id
                    n=len(node.value.elts)
                    self.container_lengths[container_name]=n
                    for i,elt in enumerate(node.value.elts):
                        value_source=self.get_base(elt)
                        if value_source:
                            self.container_items[(container_name,i)]=value_source
        if isinstance(node.value,ast.Set): #集合
            for target in node.targets:
                if isinstance(target,ast.Name):
                    container_name=target.id
                    bases=set()
                    for elt in node.value.elts:
                        base=self.get_base(elt)
                        if base:
                            bases.add(base)
                    if bases:
                        self.container_set_sources[container_name]=bases
        right=self.trace_source(node.value)
        if right:
            for target in node.targets:
                if isinstance(target,ast.Name):
                    self.symbols.add(target.id,right)
                elif isinstance(target, ast.Attribute):
                    name=self._attribute_name(target)
                    if name and name.startswith("self."):
                        self.symbols.add(name,right)
        self.generic_visit(node)

    def visit_Call(self,node):
        api_string=self.get_call(node)
        base=self._resolve_methods(node) 
        if base is None: 
            call_lookup_base=self.get_base(node,call_lookup=True)
            if call_lookup_base is not None: #如self.session.a.get(url)
                base=call_lookup_base
            else: #如_returns_requests_get()(url)
                base=self.get_base(node.func)
        if base: #如client.get_user(1)
            top=self.symbols.get_top(base)
            if top:
                if self._func_stack:
                    current_func=self._func_stack[-1]
                    if current_func not in self.function_call_tops:
                        self.function_call_tops[current_func]=set()
                    self.function_call_tops[current_func].add(top)
                print(f"调用:{api_string}")
                print(f"基符号:{base}")
                print(f"顶层库:{top}")
                print()
                self.api_calls.append({
                    'api':api_string,
                    'top':top,
                    'chain':self.symbols.get_chain(base),
                    'base':base
                })
        self.generic_visit(node)

    def get_call(self,node):
        func_str=ast.unparse(node.func)
        args_str=ast.unparse(node.args)
        result=f"{func_str}({args_str})"
        if node.keywords:
            kw_args=[]
            for kw in node.keywords:
                if kw.arg:
                    kw_args.append(f"{kw.arg}={ast.unparse(kw.value)}")
                else:
                    kw_args.append(f"**{ast.unparse(kw.value)}")
            if node.args:
                result+=f",{','.join(kw_args)}"
            else:
                result=f"{func_str}({','.join(kw_args)})"
        return result

    def visit_Attribute(self,node):
        attr_string=ast.unparse(node)
        name=self._attribute_name(node)
        if name and name in self.symbols.direct:
            base=name
        else:
            base=self.get_base(node)
        if base:
            top=self.symbols.get_top(base)
            if top:
                self.attr_accesses.append({
                    'attr':attr_string,
                    'top':top,
                    'chain':self.symbols.get_chain(base)
                })
        self.generic_visit(node)

    def visit_FunctionDef(self,node):
        self.local.add(node.name)
        self.symbols.add(node.name,"local")
        for arg in (getattr(node.args,"posonlyargs",[])+node.args.args+getattr(node.args,"kwonlyargs",[])):
            if arg.arg!="self":
                self.symbols.add(arg.arg,"local")
        if getattr(node.args,"vararg",None) is not None and node.args.vararg.arg!="self":
            self.symbols.add(node.args.vararg.arg,"local")
        if getattr(node.args,"kwarg",None) is not None and node.args.kwarg.arg!="self":
            self.symbols.add(node.args.kwarg.arg,"local")
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()
        for deco in node.decorator_list:
            deco_source=self._decorator_source(deco)
            self._bind_decorated_target(node.name,deco_source)

    def visit_AsyncFunctionDef(self,node):
        self.local.add(node.name)
        self.symbols.add(node.name,"local")
        for arg in (getattr(node.args,"posonlyargs",[])+node.args.args+getattr(node.args,"kwonlyargs",[])):
            if arg.arg!="self":
                self.symbols.add(arg.arg,"local")
        if getattr(node.args,"vararg",None) is not None and node.args.vararg.arg!="self":
            self.symbols.add(node.args.vararg.arg,"local")
        if getattr(node.args,"kwarg",None) is not None and node.args.kwarg.arg!="self":
            self.symbols.add(node.args.kwarg.arg,"local")
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()
        for deco in node.decorator_list:
            deco_source=self._decorator_source(deco)
            self._bind_decorated_target(node.name,deco_source)

    def visit_ClassDef(self,node):
        self.local.add(node.name)
        self.symbols.add(node.name,"local")
        methods=[]
        bases=[]
        for item in node.body:
            if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
                methods.append(item.name)
        for base_node in node.bases:
            base_symbol=None
            if isinstance(base_node,ast.Name): #如Class1(Class2)
                base_symbol=base_node.id
            elif isinstance(base_node,ast.Attribute): #如Class1(requests.Class3)
                base_symbol=self._attribute_name(base_node) or self.get_base(base_node)
            else:
                base_symbol=self.get_base(base_node)
            if base_symbol:
                bases.append(base_symbol)
        self.class_methods[node.name]=methods
        self.class_bases[node.name]=bases
        self.generic_visit(node)
        for deco in node.decorator_list:
            deco_source=self._decorator_source(deco)
            self._bind_decorated_target(node.name,deco_source)

    def visit_With(self,node):
        for item in node.items:
            source=self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._bind_target_to_source(item.optional_vars,source)
        self.generic_visit(node)

    def visit_AsyncWith(self,node):
        for item in node.items:
            source=self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._bind_target_to_source(item.optional_vars,source)
        self.generic_visit(node)

    def visit_For(self,node):
        source=self._iter_source(node.iter)
        self._bind_target_to_source(node.target,source)
        self.generic_visit(node)

    def visit_AsyncFor(self,node):
        source=self._iter_source(node.iter)
        self._bind_target_to_source(node.target,source)
        self.generic_visit(node)

    def visit_Return(self,node):
        if self._func_stack and node.value is not None:
            func_name=self._func_stack[-1]
            if not isinstance(node.value,ast.Constant):
                source=None
                if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name):
                    callee=node.value.func.id
                    callee_source=self.symbols.direct.get(callee)
                    if callee_source=="local" and node.value.args:
                        arg_source=self.trace_source(node.value.args[0])
                        if arg_source and arg_source in self.symbols.direct:
                            source=arg_source
                if source is None:
                    source=self.trace_source(node.value)
                if source and source in self.symbols.direct:
                    self.symbols.add(func_name,source)
        self.generic_visit(node)

    def print_results(self):
        print("符号表：")
        for symbol in self.symbols.direct:
            top= self.symbols.get_top(symbol)
            if top:
                print(f"{symbol}->{top}")
        print()
        print("符号调用链：")
        for symbol,chain in self.symbols.chains.items():
            if chain:
                chain_str='->'.join(map(str,chain))
            print(f"{symbol}:{chain_str}")
        print()
        print("函数调用：")
        if self.api_calls:
            for call in self.api_calls:
                print(f"{call['api']} 的顶层库：{call['top']}")

def analyse(source):
        tree = ast.parse(source)
        tracer = APITracer()
        tracer.visit(tree)
        return tracer