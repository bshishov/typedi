from typing import Type, Callable, Dict, Any, get_type_hints, TypeVar, Generic

__all__ = [
    'Container',
    'container',
    'InstanceSpec',
    'ProviderSpec',
    'ClassSpec'
]
__version__ = '0.1'
__author__ = 'Boris Shishov'


T = TypeVar('T')


class Container:
    def __init__(self):
        self._registry: Dict[Type, 'Spec'] = {}

    def get_instance(self, typ: Type[T], *args, **kwargs) -> T:
        return self._registry[typ].get_instance(self, *args, **kwargs)

    def bind_to_class(self, typ: Type[T], cls: Type[T]):
        assert issubclass(cls, typ)
        self._registry[typ] = ClassSpec(cls)

    def register_class(self, cls: Type[T]):
        self._registry[cls] = ClassSpec(cls)

    def bind_to_instance(self, typ: Type[T], instance: T):
        if not isinstance(instance, typ):
            raise TypeError(f'Instance should be of type {typ}')
        self._registry[typ] = InstanceSpec(instance)

    def bind_to_provider(self, typ: Type[T], provider: Callable[..., T]):
        self._registry[typ] = ProviderSpec(provider)


class Spec(Generic[T]):
    def __call__(self, c: Container, *args, **kwargs) -> T:
        return self.get_instance(c, *args, **kwargs)

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        raise NotImplementedError


class InstanceSpec(Spec[T]):
    def __init__(self, instance):
        self._instance = instance

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        return self._instance


class ProviderSpec(Spec[T]):
    def __init__(self, provider: Callable[..., T]):
        self._provider = provider
        self._annotations = get_type_hints(provider)

        if 'return' in self._annotations:
            del self._annotations['return']

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs:
                kwargs[param_name] = c.get_instance(param_type)
        return self._provider(*args, **kwargs)


class ClassSpec(Spec[T]):
    def __init__(self, typ: Type[T]):
        self._class = typ
        try:
            self._annotations = get_type_hints(self._class.__init__)
        except AttributeError:
            self._annotations = {}

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs:
                kwargs[param_name] = c.get_instance(param_type)
        return self._class(*args, **kwargs)


container = Container()
