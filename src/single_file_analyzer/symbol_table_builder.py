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
            print(f"符号链:{'->'.join(chain)}")

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
        self.container_items={}
        self.container_set_sources={}

    def visit_Import(self,node):
        for alias in node.names:
            symbol=alias.asname if alias.asname else alias.name
            self.symbols.add(symbol,alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self,node):
        for alias in node.names:
            symbol=alias.asname if alias.asname else alias.name
            self.symbols.add(symbol,node.module)
        self.generic_visit(node)

    def trace_source(self,node):
        if isinstance(node,ast.Name):
            return node.id
        elif isinstance(node,ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0])
            return self.get_base(node.func)
        elif isinstance(node,ast.Attribute):
            return self.get_base(node)
        elif isinstance(node,ast.Lambda):
            return self.get_base(node.body)
        elif isinstance(node,ast.Subscript):
            container_name=self.get_base(node.value)
            key_value=self._get_slice(node.slice)
            if container_name and key_value is not None:
                lookup_key=(container_name,key_value)
                if lookup_key in self.container_items:
                    return self.container_items[lookup_key]
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

    def get_base(self,node):
        if isinstance(node,ast.Name):
            return node.id
        elif isinstance(node,ast.Attribute):
            current=node
            while isinstance(current,ast.Attribute):
                current=current.value
            if isinstance(current,ast.Name):
                return current.id
        elif isinstance(node,ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0])
            return self.get_base(node.func)
        elif isinstance(node,ast.Lambda):
            return self.get_base(node.body)
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
        if isinstance(node.value,(ast.List,ast.Tuple)): #列表或元组
            for target in node.targets:
                if isinstance(target,ast.Name):
                    container_name=target.id
                    n=len(node.value.elts)
                    for i,elt in enumerate(node.value.elts):
                        value_source=self.get_base(elt)
                        if value_source:
                            self.container_items[(container_name,i)]=value_source
                            self.container_items[(container_name,i-n)]=value_source
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
        self.generic_visit(node)

    def visit_Call(self,node):
        api_string=self.get_call(node)
        base=self.get_base(node.func)
        if base:
            top=self.symbols.get_top(base)
            if top:
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
        base= self.get_base(node)
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
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()

    def visit_AsyncFunctionDef(self,node):
        self.local.add(node.name)
        self.symbols.add(node.name, "local")
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()

    def visit_ClassDef(self,node):
        self.local.add(node.name)
        self.symbols.add(node.name,"local")
        self.generic_visit(node)

    def visit_Return(self,node):
        if self._func_stack and node.value is not None:
            func_name=self._func_stack[-1]
            if not isinstance(node.value,ast.Constant):
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
                chain_str='->'.join(chain)
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