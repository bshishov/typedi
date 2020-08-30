# typedi

![Build](https://github.com/bshishov/typedi/workflows/Build/badge.svg)
[![PyPI version](https://badge.fury.io/py/typedi.svg)](https://badge.fury.io/py/typedi)
[![Coverage Status](https://coveralls.io/repos/github/bshishov/typedi/badge.svg?branch=master)](https://coveralls.io/github/bshishov/typedi?branch=master)

Simple yet powerful typed dependency injection container.

To install from python package index simply type (no dependencies):
```
pip install typedi
```

Or if you don't want to bring a dependency inside your project simply copy and paste `typedi.py` file (and dont forget the tests).

## Usage
### Common usage scenario

*config.py*
```python
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    host: str
    username: str
    password: str

@dataclass
class AppConfig:
    debug: bool = False 
```

*app.py*
```python
from config import DatabaseConfig, AppConfig

class Application:
    def __init__(self, app_conf: AppConfig, db_config: DatabaseConfig):
        pass

    def run(self):
        pass
```

*main.py*
```python
from typedi import Container

from config import DatabaseConfig, AppConfig
from app import Application

def load_db_config_from_file() -> DatabaseConfig:
    # Load config from file... and intantiate a config object
    return DatabaseConfig(host='localhost', username='user', password='pass')

if __name__ == '__main__':
    container = Container()
    container.register_singleton_factory(load_db_config_from_file)
    container.register_singleton_class(AppConfig)
    container.register_class(Application)
    
    # When accessing the instance typedi will automatically resolve all required dependencies
    # provided in __init__ annotations
    application_with_initialized_configs = container.get_instance(Application)
    application_with_initialized_configs.run()
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
instance2 = container.get_instance(MyClass)
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
instance = container.get_instance(MyClass)
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
instance = container.get_instance(SomeBaseClass)  # type: MyClass
```

### Features

typedi also has support of various features:

* Factory functions
* Singletons support, both for classes and factory functions
* Optionals support - ability to implement "try resolve or return None if no dependency" behavior
* Instantiation kwargs - ability to override default kwargs or resolution of kwargs
* Container nesting
* Configurable container storage

If you want to learn more, please refer to typedi_tests and actual implementation since it is quite self-describing :)

## Testing
We are using tox (and pytest) to test among multiple python versions. To run test suites and generate coverage reports simply execute
```bash
tox
```

If you don't have tox installed, execute `pip install tox` first.
