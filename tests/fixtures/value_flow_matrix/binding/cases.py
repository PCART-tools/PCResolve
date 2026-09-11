## @package cases
# Binding gold assumes ordinary Python execution of this closed fixture.
# Method entry fixtures use the defining class, without monkey patches/subclasses.
import helpers as toolkit
from helpers import identity as imported_identity
from helpers import positional, keywords, defaulted, variadic
from helpers import keyword_variadic, after_star
from facade import exported
from missing_fixture_dependency import external


## @return The second positional-only input.
def positional_only(x, y):
    return positional(x, y)


## @return The value bound to right, independent of keyword spelling order.
def keyword_only(x, y):
    return keywords(right=y, left=x)


## @return x; y is never passed to the callee.
def default_argument(x, y):
    return defaulted(x)


## @return The second extra positional argument, y.
def variadic_argument(x, y):
    return variadic(None, x, y)


## @return The right value, y, from the keyword parameter dictionary.
def variadic_keyword(x, y):
    return keyword_variadic(left=x, right=y)


## @return y after a fully known tuple expansion.
def literal_star(x, y):
    return positional(*(x, y))


## @return y; an unknown positional expansion does not change result binding.
def star_and_keyword(items, y):
    return after_star(*items, result=y)


## @return y after a fully known keyword dictionary expansion.
def literal_keywords(x, y):
    return keywords(**{'left': x, 'right': y})


## @return x via a module import alias.
def module_alias(x):
    return toolkit.identity(x)


## @return x via a function import alias.
def function_alias(x):
    return imported_identity(x)


## @return x via two explicit reexport modules.
def reexport_chain(x):
    return exported(x)


## @return x via a local alias of an imported function.
def local_alias(x):
    chosen = imported_identity
    return chosen(x)


## @return An unavailable callback's result, with unknown dependence on x.
def rebound_import(callback, x):
    imported_identity = callback
    return imported_identity(x)


## @return Only the second call result, derived from y.
def repeated_calls(x, y):
    toolkit.identity(x)
    result = toolkit.identity(y)
    return result


## Nominal instance-method fixtures.
class Worker:
    ## @return data unchanged.
    def echo(self, data):
        return data

    ## @return x through a bound method.
    def direct(self, x):
        return self.echo(x)

    ## @return x through an alias of self.
    def alias(self, x):
        receiver = self
        return receiver.echo(x)


## Standard builtin descriptor fixtures.
class Descriptors:
    ## @return data unchanged, without an implicit instance argument.
    @staticmethod
    def static_echo(data):
        return data

    ## @return data unchanged, after implicit class argument binding.
    @classmethod
    def class_echo(cls, data):
        return data


## @return x through a statically named staticmethod.
def static_descriptor(x):
    return Descriptors.static_echo(x)


## @return x through a statically named classmethod.
def class_descriptor(x):
    return Descriptors.class_echo(x)


## Parent whose implementation preserves its input.
class Base:
    ## @return data unchanged.
    def echo(self, data):
        return data


## Child using an inherited method.
class Inherited(Base):
    ## @return x from Base.echo.
    def run(self, x):
        return self.echo(x)


## Child deliberately overriding the parent's first-value behavior.
class Override(Base):
    ## @return second, discarding first.
    def echo(self, first, second):
        return second

    ## @return y from the overriding implementation.
    def run(self, x, y):
        return self.echo(x, y)


## Child demonstrating explicit and super-based parent dispatch.
class ParentDispatch(Base):
    ## @return x through explicit unbound parent method invocation.
    def explicit(self, x):
        return Base.echo(self, x)

    ## @return x through super's statically available parent method.
    def via_super(self, x):
        return super().echo(x)


## @return A callable whose output ignores all original arguments.
def replace(original):
    ## @return A constant value.
    def replacement(data):
        return None
    return replacement


## @return At runtime, replace installs a constant-returning replacement.
@replace
def replaced_identity(data):
    return data


## @return A constant from the decorator's replacement, not x.
def decorated_replacement(x):
    return replaced_identity(x)


## @return An external call's result; dependence on x is intentionally unknown.
def unavailable_definition(x):
    return external(x)
