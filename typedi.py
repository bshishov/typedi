from typing import Optional, Type, Callable, Dict, get_type_hints, TypeVar, Generic
import inspect

__all__ = [
    'Container',
    'container',
    'InstanceSpec',
    'FactorySpec',
    'ClassSpec',
    'SingletonSpec',
    'SingletonClassSpec',
    'SingletonFactorySpec',
    'Storage'
]

T = TypeVar('T')


def _get_return_type(fn: Callable[..., T]) -> Type[T]:
    return get_type_hints(fn)['return']


class Storage:
    def get(self, key: Type[T]) -> 'Spec[T]':
        raise NotImplementedError

    def set(self, key: Type[T], spec: 'Spec[T]'):
        raise NotImplementedError


class DictStorage(Storage):
    def __init__(self):
        self._spec_dict: Dict[Type, 'Spec'] = {}

    def set(self, key: Type[T], spec: 'Spec[T]'):
        self._spec_dict[key] = spec

    def get(self, key: Type[T]) -> 'Spec[T]':
        return self._spec_dict[key]


class MroStorage(DictStorage):
    def set(self, key: Type[T], spec: 'Spec[T]'):
        if inspect.isclass(key):
            for base in inspect.getmro(key):
                self._spec_dict[base] = spec
        else:
            self._spec_dict[key] = spec


class Container:
    def __init__(self, parent: Optional['Container'] = None, storage: Optional[Storage] = None):
        self.parent = parent
        self._storage = storage or MroStorage()

        # Register self, so that client code can access the instance of a container
        # that has provided dependencies during instance resolving (if requested)
        self.register_instance(self)

    def get_instance(self, key: Type[T], *args, **kwargs) -> T:
        return self.get_spec(key).get_instance(self, *args, **kwargs)

    def get_spec(self, key: Type[T]) -> 'Spec[T]':
        try:
            return self._storage.get(key)
        except KeyError as err:
            if self.parent is not None:
                return self.parent.get_spec(key)
            raise err

    def register_instance(self, instance: T, key: Optional[Type[T]] = None) -> 'InstanceSpec[T]':
        key = key or type(instance)
        if not isinstance(instance, key):
            raise TypeError(f'Instance should be of type {key}')
        spec = InstanceSpec(instance)
        self._storage.set(key, spec)
        return spec

    def register_class(self, cls: Type[T], key: Optional[Type[T]] = None) -> 'ClassSpec[T]':
        key = key or cls
        if not issubclass(cls, key):
            raise TypeError(f'Instance should be of type {key}')
        spec = ClassSpec(cls)
        self._storage.set(key, spec)
        return spec

    def register_singleton_class(self, cls: Type[T],
                                 key: Optional[Type[T]] = None) -> 'SingletonClassSpec[T]':
        key = key or cls
        if not issubclass(cls, key):
            raise TypeError(f'Instance should be of type {key}')
        spec = SingletonClassSpec(cls)
        self._storage.set(key, spec)
        return spec

    def register_factory(self, factory: Callable[..., T],
                         key: Optional[Type[T]] = None) -> 'FactorySpec[T]':
        key = key or _get_return_type(factory)
        spec = FactorySpec(factory)
        self._storage.set(key, spec)
        return spec

    def register_singleton_factory(self, factory: Callable[..., T],
                                   key: Optional[Type[T]] = None) -> 'SingletonFactorySpec[T]':
        key = key or _get_return_type(factory)
        spec = SingletonFactorySpec(factory)
        self._storage.set(key, spec)
        return spec

    def make_child_container(self):
        return Container(self, storage=self._storage.__class__())


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
        self._kwargs = {}

        if 'return' in self._annotations:
            del self._annotations['return']

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs and param_name not in self._kwargs:
                kwargs[param_name] = c.get_instance(param_type)
        return self._factory(*args, **self._kwargs, **kwargs)

    def set_kwargs(self, **kwargs):
        self._kwargs = kwargs


class ClassSpec(Spec[T]):
    def __init__(self, cls: Type[T]):
        if not inspect.isclass(cls):
            raise TypeError(f'Expected class type, got {cls} instead')
        self._class = cls
        self._kwargs = {}

        try:
            self._annotations = get_type_hints(self._class.__init__)
        except AttributeError:
            self._annotations = {}

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs and param_name not in self._kwargs:
                kwargs[param_name] = c.get_instance(param_type)
        return self._class(*args, **self._kwargs, **kwargs)

    def set_kwargs(self, **kwargs):
        self._kwargs = kwargs


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
