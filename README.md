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

To learn more I suggest reading [Inversion of Control Containers and the Dependency Injection pattern](Inversion of Control Containers and the Dependency Injection pattern) by Martin Fowler.

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
From looking at object initializers `typedi` figures out dependencies and tries its best to provide them.

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
* `...` - is any valid annotated signature with 0 or more arguments with definitions:  
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
* `Callable` classes
* `@dataclass`, `@attrs`

Not supported return annotations:
* `Final`
* `Literal`
* `Annotated`
* `Protocol`
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



## Examples
### Application with dependency

```python
# app.py
class BaseApiClient:
    def get_data(self):
        raise NotImplementedError
  

class RealApiClient(BaseApiClient):
    def __init__(self, key: str, timeout: float):
        self.key = key
        self.timeout = timeout
        
    def get_data(self):
        print(f"Calling api with {self.key}")

        
class Service:
    def __init__(self, api_client: BaseApiClient):  # note, a base class is used
        self.api_client = api_client                

        
class Application:
    def __init__(self, service: Service):
        self.service = service
        
    def run(self):
        pass


if __name__ == '__main__':
    from typedi import Container
    
    container = Container()
    container.register_instance(RealApiClient(key="somekey", timeout=5.0))
    container.register_class(Service)
    container.register_class(Application)    
    
    # Resolves application instance and all its dependencies
    # Container will recognize that Application need Service which needs BaseApiClient
    # There is a RealApiClient that matches `BaseApiClient` query.
    # So a Service with RealApiClient is constructed.
    app = container.resolve(Application)
    
    app.run()

# test_app.py

class FakeApiClient(BaseApiClient):
    def get_data(self):
        print("Getting test data")
        return {"test": 123}
    

def test_app():
    container = Container()
    container.register_instance(FakeApiClient())
    container.register_class(Service)
    container.register_class(Application)
    
    # Resolves application instance and all its dependencies
    # FakeApiClient will be used instead of RealApiClient
    app = container.resolve(Application)
    
    app.run()  
    # todo: assert something

```

### Containers

You can create your own container DI container that will store instances/factories you provide:

```python
from typedi import Container

container = Container()
```

typedi does not come with a shared container since not to encourage the use of global state. In fact, you should take care of sharing container across modules if you want to implement service-locator pattern.

### Instance bindings, "user-managed singletons"

Containers could act as a simple key-value storage for instances where the key is actually a type of that instance, you register an instance first, then ask for a type to get the instance.

```python
from typedi import Container


class MyClass:
    pass


instance = MyClass()
container = Container()
container.register_instance(instance)
instance2 = container.resolve(MyClass)
```

### Class bindings

Note that instead of registering an actual instance you could register a class acting as a factory of instances.
Then when an instance is requested, a class would be instantiated (with all init args resolved) and returned.

```python
from typedi import Container


class MyClass:
    pass


container = Container()
container.register_class(MyClass)
instance = container.resolve(MyClass)
```

### Class bindings with inheritance

The main strength of DI containers is ability to decouple dependencies by sharing common interface while user of an object does not care about actual implementation.

```python
from typedi import Container


class SomeBaseClass:
    pass


class MyClass(SomeBaseClass):
    pass


container = Container()

# here we register MyClass as a class binding
# It is factory of both MyClass objects and SomeBaseClass objects (using MRO)
container.register_class(MyClass)

# Note that we ask for a base class but container will actually instantiate a MyClass object
# since container knows the base classes of MyClass
instance = container.resolve(SomeBaseClass)  # type: MyClass
```

### Features

typedi also has support of various features:

* Factory functions (including `functools.partial`)
* Singletons support, both for classes and factory functions
* Optionals support - ability to implement "try resolve or return None if no dependency" behavior

If you want to learn more, please refer to typedi_tests and actual implementation since it is quite self-describing :)

## Testing
We are using tox (and pytest) to test among multiple python versions. To run test suites and generate coverage reports simply execute
```bash
tox
```

If you don't have tox installed, execute `pip install tox` first.
