# API Call Chain Tracing for Python Third-Party Libraries Based on Static Analysis 2026.4.2

## Project Overview
The project aims to implement API call chain tracing for Python third-party libraries based on static analysis.

## Project Progress

### Project Timeline
- [x] Implement scanning of project directories and mapping of file paths to module names based on the `getPath` file from the PCART project.
- [x] Build an AST using the `ast` module to parse project source code, implement a basic single-file analyzer to extract fundamental API call patterns.
- [x] Implement complete tracing of symbol source chains and call chains within a single file.
- [x] Design a global symbol table based on the single-file symbol table and module mapper to enable cross-file symbol tracing.
- [ ] Extend support for various API call forms by designing dedicated analysis modules for complex invocation patterns.
- [ ] Introduce flow‑sensitive analysis to improve symbol resolution accuracy,using control flow graphs built from the AST to analyze execution paths.
- [ ] Integrate and refine the above components to implement a complete call analyzer and test it on real‑world projects.

### Supported API Call/Tracing Types
- [x] **Direct import+direct call**:fully supported
- [x] **From/as import+alias call**:fully supported
- [ ] **Variable binding/container storage/closure capture**:mostly supported;mixed sets need adjustments;dictionaries support constant keys
- [x] **partial/lambda(lightweight wrappers)**:fully supported
- [ ] **Object‑oriented encapsulation & inheritance**: partially supported
- [x] **Cross‑file shared third‑party instances**:fully supported
- [ ] **Decorator pattern**:not supported
- [ ] **Context managers/protocols**:partially supported(can recognize third‑party constructor calls like `requests.Session()`,but not `session.get(...)` yet)
- [ ] **Chained calls/Fluent API/sub‑resource objects**:partially supported; the origin of the root object can usually be determined
- [ ] **Reflection/getattr/importlib dynamic calls**:not supported
- [ ] **Plugin registries/configuration‑driven calls**:partially supported(currently only recognizes third‑party calls written directly inside registration functions)
- [ ] **Monkey patch/mock patch**:not supported
- [ ] **Descriptors/metaclasses/ORM‑style implicit calls**:partially supported (calls directly written inside these methods can be traced)
- [ ] **Eval/exec/AST dynamic execution**:not supported

## Output
- Global symbol table(symbol→ultimate source)
- Global trace chain(how symbols recursively resolve to the ultimate source via aliases/return values)
- Calls(call expression + top‑level source library)
- Parsed AST tree

## How to Run
Run `main.py` and input the absolute path to the project root directory.

## Runtime Environment
- Operating system tested:Windows 10(x64)
- Python version:3.11+
- Dependency installation:no extra third-party dependencies required for this project itself
- Python standard libraries used:`ast`,`os`,`sys`,`copy`,`builtins`,`typing`
- Input requirement:provide an absolute path to a Python project directory

