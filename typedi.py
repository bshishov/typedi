from typing import Optional, Type, Callable, Dict, Any, get_type_hints, TypeVar, Generic, overload
import inspect

__all__ = [
    'Container',
    'container',
    'InstanceSpec',
    'FactorySpec',
    'ClassSpec'
]

T = TypeVar('T')


class Container:
    def __init__(self, parent: Optional['Container'] = None):
        self.parent = parent
        self._storage: Dict[Type, 'Spec'] = {}

        # Register self, so that client code can access the container
        # that has provided dependencies (if requested)
        self.register_class(self.__class__)

    def get_instance(self, key: Type[T], *args, **kwargs) -> T:
        return self.get_spec(key).get_instance(self, *args, **kwargs)

    def get_spec(self, key: Type[T]) -> 'Spec[T]':
        try:
            return self._storage[key]
        except KeyError as err:
            if self.parent is not None:
                return self.parent.get_spec(key)
            raise err

    def register_instance(self, key: Type[T], instance: T):
        if not isinstance(instance, key):
            raise TypeError(f'Instance should be of type {key}')
        self._storage[key] = InstanceSpec(instance)

    def register_class(self, key: Type[T], cls: Optional[Type[T]] = None):
        cls = cls or key
        if not issubclass(cls, key):
            raise TypeError(f'Instance should be of type {key}')
        self._storage[key] = ClassSpec(cls)

    def register_singleton_class(self, key: Type[T], cls: Optional[Type[T]] = None):
        cls = cls or key
        if not issubclass(cls, key):
            raise TypeError(f'Instance should be of type {key}')
        self._storage[key] = SingletonClassSpec(cls)

    def register_factory(self, key: Type[T], factory: Callable[..., T]):
        self._storage[key] = FactorySpec(factory)

    def register_singleton_factory(self, key: Type[T], factory: Callable[..., T]):
        self._storage[key] = SingletonFactorySpec(factory)

    def make_child_container(self):
        return Container(self)


class Spec(Generic[T]):
    def __call__(self, c: Container, *args, **kwargs) -> T:
        return self.get_instance(c, *args, **kwargs)

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        raise NotImplementedError


class InstanceSpec(Spec[T]):
    def __init__(self, instance: T):
        self._instance = instance

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        return self._instance


class FactorySpec(Spec[T]):
    def __init__(self, factory: Callable[..., T]):
        self._factory = factory
        self._annotations = get_type_hints(factory)

        if 'return' in self._annotations:
            del self._annotations['return']

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs:
                kwargs[param_name] = c.get_instance(param_type)
        return self._factory(*args, **kwargs)


class ClassSpec(Spec[T]):
    def __init__(self, cls: Type[T]):
        if not inspect.isclass(cls):
            raise TypeError(f'Expected class type, got {cls} instead')
        self._class = cls
        try:
            self._annotations = get_type_hints(self._class.__init__)
        except AttributeError:
            self._annotations = {}

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs:
                kwargs[param_name] = c.get_instance(param_type)
        return self._class(*args, **kwargs)


class SingletonSpec(Spec[T]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._instance: T = None

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        if self._instance is None:
            self._instance = super().get_instance(c, *args, **kwargs)
        return self._instance


class SingletonFactorySpec(SingletonSpec[T], FactorySpec[T]):
    pass


class SingletonClassSpec(SingletonSpec[T], ClassSpec[T]):
    pass


container = Container()
