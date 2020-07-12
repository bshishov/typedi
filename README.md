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
from typedi import container

from config import DatabaseConfig, AppConfig
from app import Application

def load_db_config_from_file() -> DatabaseConfig:
    # Load config from file... and intantiate a config object
    return DatabaseConfig(host='localhost', username='user', password='pass')

if __name__ == '__main__':
    container.register_singleton_factory(load_db_config_from_file)
    container.register_singleton_class(AppConfig)
    container.register_class(Application)
    
    # When accessing the instance typedi will automatically resolve all required dependencies
    # provided in __init__ annotations
    application_with_initialized_configs = container.get_instance(Application)
    application_with_initialized_configs.run()
```


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
container.register_instance(instance)

# anywhere else
from typedi import container

instance = container.get_instance(MyClass)
```

### Class bindings
```python
from typedi import container

class MyClass:
    pass

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

container.register_class(ChildOfMyClass)

# anywhere else
from typedi import container

auto_instantiated_instance = container.get_instance(MyClass)  # type: ChildOfMyClass
```

## Testing
We are using tox (and pytest) to test among multiple python versions. To run test suites and generate coverage reports simply execute
```bash
tox
```

If you don't have tox installed, execute `pip install tox` first.
