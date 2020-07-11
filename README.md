# typedi

![Build](https://github.com/bshishov/typedi/workflows/Build/badge.svg)

Simple typed dependency injection container.

To install from python package index simply type (no dependencies):
```
pip install typedi
```

Or, if you don't want to bring a dependency inside a project simply copy and paste `typedi.py` inside your project

## Usage
### Containers

typedi comes with a default shared container, to add or retrieve instances from it import it anywhere you need - usually in some initialization/bootstrapping logic.
 
 ```python
from typedi import container
```

Or you could also create your own DI containers:

```python
from typedi import Container

my_container = Container()
```

### Instance bindings, "user-managed singletons"
```python
from typedi import container

class MyClass:
    pass

instance = MyClass()
container.bind_to_instance(MyClass, instance)

# anywhere else
from typedi import container

instance = container.get_instance(MyClass)
```

### Class bindings
```python
from typedi import container

class MyClass:
    pass

instance = MyClass()
container.register_class(MyClass)

# anywhere else
from typedi import container

auto_instantiated_instance = container.get_instance(MyClass)
```

### Class bindings with inheritance
```python
from typedi import container

class MyClass:
    pass

class ChildOfMyClass(MyClass):
    pass

instance = MyClass()
container.bind_to_class(MyClass, ChildOfMyClass)

# anywhere else
from typedi import container

auto_instantiated_instance = container.get_instance(MyClass)  # type: ChildOfMyClass
```