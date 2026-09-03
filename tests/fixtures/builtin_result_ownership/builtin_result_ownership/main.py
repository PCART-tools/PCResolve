# Test fixture: builtin call ownership vs result ownership
# Patterns from builtin-contamination-audit.md

class LocalClass:
    pass

# Pattern 1: eval() — call owner = python, result = unknown
factory = eval("LocalClass")
factory()

# Pattern 2: next() — call owner = python, result = element-derived
value = next(iter([1]))
value.bit_length()

# Pattern 3: min() — call owner = python, result = element-derived
value2 = min([LocalClass(), LocalClass()])
value2.method()

# Pattern 4: getattr() — call owner = python, result = receiver-attribute-derived
factory2 = getattr(LocalClass, "__init__")
factory2()

# Pattern 5: type(obj) — call owner = python, result from obj
obj = LocalClass()
cls = type(obj)
cls()

# Pattern 6: __import__() — call owner = python, result = unknown (dynamic)
mod = __import__("os")
mod.getcwd()

# Pattern 7: open() — call owner = python, result = python (PYTHON_OWNED_RESULT)
f = open("/dev/null")
f.write("data")

# Pattern 8: super().__init__() — bare super() = python, method from base class
class Child(LocalClass):
    def __init__(self):
        super().__init__()

# Pattern 9: enumerate() in for-loop — call owner = python, yields from container
items = [LocalClass(), LocalClass()]
for i, x in enumerate(items):
    x.method()
