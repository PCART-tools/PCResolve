# PCResolve — Python API Call Chain Tracing

Static analysis tool that traces every API call in a Python project back to its origin library (e.g. `requests`, `numpy`, `flask`). Each call is classified by **definition origin** (not data flow): a locally defined function is `local` even if it internally calls third-party APIs. Other classifications include `python` for builtins and the top-level library name for third-party / stdlib calls. When container iteration produces ambiguous candidates, the result is a merged label like `[requests,numpy]`.

[![PyPI](https://img.shields.io/pypi/v/pcresolve)](https://pypi.org/project/pcresolve/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install pcresolve
```

For development:

```bash
pip install -e .
```

No third-party dependencies — pcresolve uses only the Python standard library (`ast`, `os`, `sys`, `builtins`, `copy`, `typing`).

Requires Python 3.9+.

## Quick Start

### CLI

```bash
# Human-readable output
pcresolve /path/to/project

# JSON output
pcresolve --json /path/to/project

# Or as a module
python -m pcresolve /path/to/project
```

### Library API

```python
from pcresolve import analyze_project, analyze_source

# Analyze an entire project
result = analyze_project("/path/to/project")
for call in result.all_api_calls:
    print(f"{call.expression} -> {call.top_library}")

# Analyze a single source string
code = '''
import requests
resp = requests.get("https://example.com")
'''
result = analyze_source(code, file_path="example.py")
for sym, top in result.symbols.items():
    print(f"{sym} -> {top}")
```

## Public API

| Name | Description |
|------|-------------|
| `analyze_project(root)` | Full project analysis, returns `ProjectAnalysis` |
| `analyze_source(code)` | Single-file analysis, returns `FileAnalysis` |
| `scan_directory(root)` | Discover .py/.pyi files, returns `list[str]` |
| `ProjectAnalyzer(root)` | Orchestrator class (step-by-step control) |
| `SingleFileAnalyzer()` | AST visitor class for one file |
| `ModuleMapper(root)` | File-path to module-name bidirectional mapping |
| `SymbolTable()` | Per-symbol chain tracking |
| `FileScanner()` | File system scanner |

## Output Types

```python
@dataclass
class ApiCall:
    expression: str       # "requests.get('url')"
    top_library: str      # "requests", "python", "local"
    base_symbol: str      # Root symbol name
    chain: list           # Resolution chain

@dataclass
class FileAnalysis:
    file_path: str
    module_name: str
    symbols: dict         # symbol -> top-level source
    chains: dict          # symbol -> resolution chain
    api_calls: list

@dataclass
class ProjectAnalysis:
    project_root: str
    files: list
    all_api_calls: list
```

## Supported Patterns

- Direct import + direct call
- `from/as` import + alias call
- Variable binding / container storage (dict, list, tuple, set)
- `partial` / lambda wrappers
- Class encapsulation & inheritance
- Cross-file shared third-party instances
- Decorator pattern
- Context managers / protocols (`with`, `async with`)
- Chained calls / fluent API
- `getattr` / `importlib.import_module` dynamic calls
- `for` loop container iteration (with merged ambiguous candidates)
- Tuple unpacking (e.g., `a, b = connect()`)
- List / set / dict comprehension
- BinOp receiver method calls (e.g., `(a - b).method()`)
- Broken attribute chains across `Call` nodes (e.g., `.last().dt.days()`)
- Self-referencing variable reassignment (e.g., `df = df.dropna()`)
- `async def` / `async for` support
- Wildcard import from local modules

## Known Limitations

- **`partial` alias**: `a = partial; a(requests.get, ...)` resolves to `functools` instead of `requests`. The static analysis only recognizes direct `partial(...)` calls, not aliases to `partial`.
- **`self.session.get(url)`**: When `session = requests.Session()` is assigned as an instance attribute, method calls on it trace to `local` rather than the actual library. The class receiver is locally defined, so the structured tuple resolves back to `local`.
- **Multiple inheritance method attribution**: When a class inherits from multiple bases, method resolution stops at the first base that traces to an external library. A locally defined method may be misattributed if an external base class appears earlier in the MRO.
- **Container iteration in single-file mode**: `for f in {requests.get, np.sum}: f(...)` produces an unresolved structured tuple in `SingleFileAnalyzer`. Full resolution to a merged candidate like `[requests,numpy]` happens only in the cross-file stage.
- **Dynamic `import_module` with variables**: `importlib.import_module(name)` only resolves when `name` is a string literal. Variable arguments produce an unresolved result.
- **Multiple return values**: When a function has multiple `return` statements, only the first encountered return value is recorded. Later branches (e.g., `else` paths) are not tracked.

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

PCResolve is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
