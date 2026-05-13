# PCResolve — Python API Call Chain Tracing

Static analysis tool that traces every API call in a Python project back to its origin library (e.g. `requests`, `numpy`, `flask`) or identifies it as `local` / `python` builtin.

## Installation

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
    api_calls: list[ApiCall]

@dataclass
class ProjectAnalysis:
    project_root: str
    files: list[FileAnalysis]
    all_api_calls: list[ApiCall]
```

## Supported Patterns

- Direct import + direct call
- `from/as` import + alias call
- Variable binding / container storage (dict, list, tuple, set)
- `partial` / lambda wrappers
- Class encapsulation & inheritance
- Cross-file shared third-party instances
- Decorator pattern
- Context managers / protocols (with, async with)
- Chained calls / fluent API
- `getattr` / `importlib.import_module` dynamic calls

## Running Tests

```bash
python -m pytest tests/ -v
```
