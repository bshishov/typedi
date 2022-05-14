# typedi

![Build](https://github.com/bshishov/typedi/workflows/Build/badge.svg)
[![PyPI version](https://badge.fury.io/py/typedi.svg)](https://badge.fury.io/py/typedi)
[![Coverage Status](https://coveralls.io/repos/github/bshishov/typedi/badge.svg?branch=master)](https://coveralls.io/github/bshishov/typedi?branch=master)

Simple yet powerful typed annotation-based dependency injection container.

To install from python package index simply type (no dependencies):
```
pip install typedi
```

## Dependency Injection

Dependency Injection (DI) - is a design pattern where an object automatically receives other objects that it depends on.
It is an approach to implement Inversion of Control - way to separate concerns and reduce coupling.

To learn more I suggest reading [Inversion of Control Containers and the Dependency Injection pattern](https://martinfowler.com/articles/injection.html) by Martin Fowler.

When DI in python is useful (my subjective opinion):
* Large modularized applications
* Frameworks foundation
* Plugin systems

When it is harmful or might bring unnecessary complexity:
* Small applications
* Simple elegant pythonic projects
* Large untyped, poorly structured code (will require lots of refactoring in a first place)
    
## typedi

`typedi` - implements "constructor based" dependency injection by heavily utilizing python's type annotations.
This means that you specify object dependencies just by type annotations in `__init__` methods or by annotating dataclasses.

From looking at object initializers `typedi` figures out dependencies and tries its best to provide them:
```python
class AbstractService:
    pass


class ConcreteService(AbstractService):
    pass


class App:
    # App depends on AbstractService.
    # Such that we can provide multiple implementations, i.e. for testing purposes. 
    def __init__(self, service: AbstractService):  
        self.service = service


from typedi import Container
container = Container()  # creating a DI container

# Registering instance of a ConcreteService into container.
container.register_instance(ConcreteService())

# Registering App class.
# Container will inspect the signature of __init__.  
container.register_class(App)  

# First, container tries to specify dependencies of App:
#   * The container looks up registered providers for anything that matches AbstractService.
#   * There is an instance of ConcreteService which matches AbstractService, so it is a match.
# Then instance of App is created with a ConcreteService instance value for `service` argument. 
application = container.resolve(App)
```

This example is unrealistically simple. 
But it highlights the fundamental idea of specifying and resolving dependencies from type signatures.

Here is more complex example highlighting some more features:
```python
from typing import Protocol, List, runtime_checkable
from dataclasses import dataclass


# Note: we are using protocol
# Abstract classes (abc) or basic inheritance would also work
@runtime_checkable
class MathOperation(Protocol):
    def apply(self, a: int, b: int) -> int:
        ...
    

class SumOperation:   # Note: not even subclassing
    def apply(self, a: int, b: int) -> int:
        return a + b
    

class SubtractOperation:   # Note: not even subclassing
    def apply(self, a: int, b: int) -> int:
        return a - b
    

@dataclass  # dataclasses (or even attrs) are supported
class App:
    # Require instances that support MathOperation Protocol     
    operations: List[MathOperation]
    
    # Note: typedi also supports dependencies specified using complex types:
    #   List, Iterable, Union, Optional, Tuple, Type and even Any
    
    def do_something(self, a: int, b: int):
        for op in self.operations:
            print(f"{op}: {op.apply(a, b)}")
            
 
# Importing here just to highlight that it is not needed anywhere above
from typedi import Container

container = Container()

# Register operations as singletons. 
# There will be at most 1 instance in the container 
# Instances will be created only when requested.
container.register_singleton_class(SumOperation)
container.register_singleton_class(SubtractOperation)

# Registering App so that container will understand its dependencies.
container.register_class(App)

# Resolution happens here.
app = container.resolve(App)

app.do_something(3, 4)
```

`typedi` aims 0 user code invasion - your code is yours:
* no magic meta subclassing
* no decorators
* no magic `Depends` default arguments
* no magic `__` attributes

You could use `typedi` in existing application without altering existing class/factory code.

### Container

The central concept of most DI implementations including `typedi` is `Container`.
It serves two purposes:
* Stores registered dependency providers
* Provides interface to query constructed instances

To create container:

```python
from typedi import Container

container = Container()
```

### Registering providers
To be able to resolve dependencies `Container` should know how to provide them,
what instances to provide, what functions to call or what classes to instantiate.

`typedi` supports multiple different ways of registering instance providers.

* `container.register_instance(SomeClass(...))` - Container will just remember this instance and will provide it as a dependency for any object that requires type `SomeClass`. This could be considered as container-scoped singletons that you manually created.
* `container.register_factory(fn)` - instead of providing complete initialized instance you could use a factory function that creates it. Container will look at the function signature and remember that instances of return type could be created by calling `fn`.
Every time a return type is requested container will call `fn` to create an instance.
* `container.register_class(SomeClass)` - same as `container.register_factory` but for classes. Container will remember that objects of `SomeClass` or any parent type in class hierarchy could be created by instantiating `SomeClass`. 
* `container.register_singleton_factory(fn)` - same as `container.register_factory` but will be only called once per container and result will be cached.
* `container.register_singleton_class(fn)` - same as `container.register_class` but will be only called once per container and result will be cached.

Note: it is possible to register multiple providers of the same type. 

### Resolving instances
Once container knows how to provide instances you can query them.
Objects are queried from the container by some queried type.
* `container.resolve(T)` - will return an single instance of type `T`.
* `container.get_all_instances(T)` - will return a list of instances of type `T`.
* `container.iter_all_instances(T)` - will return an iterable of instances of type `T`.

In each case container will try to find providers that can provide requested type and call them if needed and return resulting instances.

If container is not able to provide an instance(s) of given type it raises `ResolutionError`.

### Supported providers

Here is the list of things recognised by the Container. This means that you can register a factory or a class that produces type `-> T` and container will be able to resolve it.   

| Signature                     | Description                                                                      |
|-------------------------------|----------------------------------------------------------------------------------|
| `A`                           | some class as a factory of its instances                                         |
| `A(...)`                      | any already created instance                                                     |
| `fn(...) -> A`                | factory of a single instance                                                     |
| `fn(...) -> Optional[T]`      | factory of and optional instance of type `T`                                     |
| `fn(...) -> Union[T1,...,Tn]` | factory of either types                                                          | 
| `fn(...) -> List[T]`          | factory of many instances of type `T`                                            | 
| `fn(...) -> Iterable[T]`      | factory of many instances of `T`, might be a be a generator as well.             |
| `fn(...) -> Tuple[T1, T2]`    | factory of tuple of `T1` and `T2` as well as `T1` and `T1` instances separately. |
| `fn(...) -> Any`              | factory of any instances (types will be runtime checked).                        |
| `fn(...) -> Type[T]`          | factory of generic meta type of `T`.                                             |
* `A` is any concrete class type.
* `T` - any supported type including concrete classes, or generics `Optional[T]`, `Union[T1, T2]`, `Iterable[T]`, `List[T]` and `Tuple[T1, ..., TN]`. Which means you can go crazy and return something like `-> Iterable[Optional[List[Union[A, B]]]]`. Container will deal with it.
* `...` - is valid annotated signature with 0 or more arguments with definitions, for example:  
  * `arg: T` - argument of some specific type `T`. If container is not able to resolve `T` it will raise `ResolutionError`.
  * `arg: Optional[T]` - if container will fail to resolve `T`, `None` value will be used. 
  * `*args: T` - varargs will be resolved as `Tuple[T]`. If it is not possible to resolve `T` - empty `tuple()` will be passed. 
  * `arg: T = default_value` - container will try to resolve `T` but if it fails, `default_value` will be used.

Container will perform a `.resolve()` for each argument by its annotation. 
For more information about resolution see below. 

Few examples of valid factory/class signatures that you can register:
```
A()
f() -> A
f(b: B) -> A
f(*args: B) -> A
f(bs: List[B]) -> A
f(b: Optional[B]) -> A
f(bs: Iterable[B]) -> A
f(b: Optional[B] = None) -> A
f(*args: B, arg: C = DEFAULT_C) -> A
f() -> Tuple[List[A], B, C]
f() -> Union[A, B, C]
f() -> Tuple[A, B, C]
f() -> Iterable[A]
f(*args: A) -> Any
f(a: A) -> A
A(a: A)
```

These could also be used as factories:
* `functlools.partial` of any typed callable
* Custom callable classes (with annotated `__call__`)
* `@dataclass`, `@attrs`

Not supported return annotations:
* `Final`
* `Literal`
* `Annotated`
* generic annotations with `TypeVar`

### Supported resolution type queries
| Query (`T`)        | Description                                                                                                                            |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| `A`                | Resolves an instance of `A`, raises `ResolutionError` if not possible                                                                  |
| `Optional[T]`      | Resolves an instance of type `T` if possible, otherwise returns `None`                                                                 |
| `Union[T1,...,Tn]` | Tries resolution of each type argument left to right, if nothing resolves raises `ResolutionError`                                     |
| `List[T]`          | Resolves all instances of `T` and returns a list. If none of `T` availble, provides empty list.                                        |
| `Iterable[T]`      | Resolves all instances of `T` into an iterable. If non of `T` available, provides empty iterable.                                      |
| `Tuple[T1,...,Tn]` | First, tries to resolve an instance of `Tuple[T1,...,Tn]` as is. If it is not available provides instances of `T1` to `Tn` as a tuple. |

`typedi` also resolves covariant types and even covariant generics like `List`, `Tuple`, `Iterable` and even higher order `Type[T]`.

Covariance example:

```python
from typing import List


class Base:
    pass


class Concrete(Base):
    pass


from typedi import Container
container = Container()

# Registering concrete instances
container.register_instance(Concrete())
container.register_instance(Concrete())

# Query all instances that are instance of Base
concrete_instances = container.resolve(List[Base])

assert isinstance(concrete_instances[0], Concrete)
assert isinstance(concrete_instances[1], Concrete)
```


## Features

typedi also has support of various features:

* Factory functions (including `functools.partial`)
* Singletons support, both for classes and factory functions
* Optionals support - ability to implement "try resolve or return None if no dependency" behavior

If you want to learn more, please refer to typedi_tests and actual implementation since it is quite self-describing :)


## Circular dependencies
`typedi` can handle circular dependencies solving "chicken and egg" problem:

```python
class A:
    def __init__(self, b: "B"):
        self.b = b

class B:
    def __init__(self, a: A):
        self.a = a

from typedi import Container
container = Container()

# Register both classes
container.register_class(A)
container.register_class(B)

a = container.resolve(A)
assert isinstance(a, A)
assert isinstance(a.b, B)

# Circular dependency
assert isinstance(a.b.a, A)
assert a.b.a == a 

assert a.b.a is not a  # NOTE: a.b.a is a proxy of a, not the exact instance
```

This code actually works. 
It is done internally by constructing a proxy object when encountering circular dependency during resolution.
The proxy is completely identical to the original. You can use proxies in the same way as the original objects.

Proxy objects are used only to resolve a circular dependency. All non-circular dependencies would resolve in original, genuine objects. 

The only restriction is that it is impossible to access the proxied circular dependencies inside the factory method (or `__init__`) itself. This code will raise an error during resolution:

```python
...

class B:
    def __init__(self, a: A):            
        print(a)  # access to method __str__ of not-yet initialized proxy instance of A        
        self.a = a

...
```

## Performance considerations

As you might have guessed already, there is a lot of introspection, reflection, `type(...)` and `isinstance(...)` going on under the hood when registering and resolving.
I do not recommend using `Container` methods in your runtime hot paths since `.resolve()` call is quite expensive and might affect performance.
Use it to assemble things on startup and throw the `Container` away.

`Container` tries its best to reduce unnecessary calls to factories. 
However, if return annotation of a provider is not strict enough (`Union`, or `Any`) in order to resolve some instance of that factory
there is no other way other than call it and just go through all the options and check if it does match the query.
Resolution complexity aligns in a way: `ConcreteType < Union[ConcreteTypeA, ConcreteTypeB] < Any`.

Another costly part is generators, if you have a generator that produces instance of types `A`, `B` and then `C`, 
resolving a `C` would also result in instantiating `A` and `B`:

```python
from typing import Union, Iterable

class A: ...
class B: ...
class C: ...

def generator() -> Iterable[Union[A, B, C]]:
    yield A()  # wasted call
    yield B()  # wasted call
    yield C()
    yield A()  # also wasted call because container caches an entire result of a factory
    
from typedi import Container
container = Container()
container.register_factory(generator)

# generator would be called, and container will go through all generated instances 
# and check isinstance(item, C), once found, instance of C will be returned
c = container.resolve(C)
assert isinstance(c, C)
```

## About python 3.6 and older
`typing` module became more or less stable only after python 3.7 (including). API for types in 3.6 differs significantly from 3.7 onward.

It is hard to maintain two different APIs that's why I decided to stick to the newer one. 
However, if you feel brave enough and really need that 3.6 support you can open a PullRequest and contact me if you have any questions.

## Testing
This project is using tox (and pytest) to test among multiple python versions. To run test suites and generate coverage reports simply execute
```bash
tox
```

If you don't have tox installed, execute `pip install tox` first.
