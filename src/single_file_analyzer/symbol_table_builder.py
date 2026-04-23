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
            getattr_src=self._resolve_getattr_trace(node)
            if getattr_src:
                return getattr_src
            import_mod=self._resolve_import_module_trace(node)
            if import_mod:
                return import_mod
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0])
            me=self._resolve_methods(node)
            if me:
                return me
            call_key=self.get_base(node,call_lookup=True) #打开
            if call_key:
                return call_key
            if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Call):
                inner_source=self.trace_source(node.func.value)
                if inner_source:
                    return inner_source
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

    def _literal_str(self,node):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            return node.value
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

    def _is_getattr_call(self,node):
        if not isinstance(node,ast.Call) or len(node.args)<2:
            return False
        func=node.func
        if isinstance(func,ast.Name) and func.id=="getattr":
            return True
        if isinstance(func,ast.Attribute) and func.attr=="getattr":
            return True
        return False

    def _resolve_getattr_trace(self,node):
        if not self._is_getattr_call(node):
            return None
        name_lit=self._literal_str(node.args[1])
        if name_lit is None:
            return None
        obj_key=self.trace_source(node.args[0])
        if obj_key is None:
            return None
        return obj_key

    def _is_importlib_module(self,symbol):
        if not isinstance(symbol,str):
            return False
        if symbol=="importlib":
            return True
        top=self.symbols.get_top(symbol)
        return top=="importlib"

    def _is_import_module_call(self,node):
        if not isinstance(node,ast.Call) or not node.args:
            return False
        func=node.func
        if isinstance(func,ast.Attribute) and func.attr=="import_module": #importlib.import_module
            root=self.get_base(func.value)
            if root and self._is_importlib_module(root):
                return True
            return False
        if isinstance(func,ast.Name) and func.id=="import_module": #import_module
            if self.import_from_symbols.get("import_module")=="importlib":
                return True
            return False
        return False

    def _resolve_import_module_trace(self,node):
        if not self._is_import_module_call(node):
            return None
        name=self._literal_str(node.args[0])
        if name is None:
            return None
        return name

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

    def _resolve_call_receiver(self,receiver_node):
        if isinstance(receiver_node,ast.Name):
            return receiver_node.id
        if isinstance(receiver_node,ast.Attribute):
            receiver_name=self._attribute_name(receiver_node)
            if receiver_name is not None:
                return receiver_name
            return self._resolve_call_receiver(receiver_node.value)
        if isinstance(receiver_node,ast.Call):
            inner_receiver=self.get_base(receiver_node,call_lookup=True)
            if inner_receiver is not None:
                return inner_receiver
            return self.get_base(receiver_node.func,call_lookup=False)
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

    def _target_to_source(self,target,source):
        if not source:
            return
        if isinstance(target,ast.Name): #x
            self.symbols.add(target.id,source)
            return
        if isinstance(target,ast.Attribute): #self.x
            name=self._attribute_name(target)
            if name and name.startswith("self."):
                self.symbols.add(name,source)
            return
        if isinstance(target,(ast.Tuple,ast.List)): #a,b
            for elt in target.elts:
                self._target_to_source(elt,source)

    def _iter_source(self,iter_node): ##for x in iter
        if isinstance(iter_node,ast.Name): 
            container_name=iter_node.id
            has_items=False
            for k in self.container_items.keys(): #容器名是否在con_items里有记录
                if k[0]==container_name:
                    has_items=True
                    break
            has_set=container_name in self.container_set_sources  #容器名是否在con_sets_sources里有记录
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
                    return self._resolve_call_receiver(func.value)
                if isinstance(func,ast.Call):
                    return self._resolve_call_receiver(func)
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

    def _resolve_call_base_for_api(self,node):
        if self._is_getattr_call(node):
            if self._literal_str(node.args[1]) is not None:
                g=self.trace_source(node.args[0])
                if g is not None:
                    return g
        if self._is_import_module_call(node):
            im=self._resolve_import_module_trace(node)
            if im is not None:
                return im
        base=self._resolve_methods(node)
        if base is not None:
            return base
        call_lookup_base=self.get_base(node,call_lookup=True)
        if call_lookup_base is not None:
            return call_lookup_base
        return self.get_base(node.func)

    def visit_Call(self,node):
        api_string=self.get_call(node)
        base=self._resolve_call_base_for_api(node)
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
        parts=[ast.unparse(a) for a in node.args]
        if node.keywords:
            for kw in node.keywords:
                if kw.arg:
                    parts.append(f"{kw.arg}={ast.unparse(kw.value)}")
                else:
                    parts.append(f"**{ast.unparse(kw.value)}")
        args_str=", ".join(parts)
        return f"{func_str}({args_str})"

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
                self._target_to_source(item.optional_vars,source)
        self.generic_visit(node)

    def visit_AsyncWith(self,node):
        for item in node.items:
            source=self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars,source)
        self.generic_visit(node)

    def visit_For(self,node):
        source=self._iter_source(node.iter)
        self._target_to_source(node.target,source)
        self.generic_visit(node)

    def visit_AsyncFor(self,node):
        source=self._iter_source(node.iter)
        self._target_to_source(node.target,source)
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