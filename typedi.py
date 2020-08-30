from typing import Optional, Type, Callable, Dict, get_type_hints, TypeVar, Generic, Tuple
import typing
import inspect

__all__ = [
    'Container',
    'InstanceSpec',
    'FactorySpec',
    'ClassSpec',
    'SingletonSpec',
    'SingletonClassSpec',
    'SingletonFactorySpec',
    'Storage',
    'ResolutionError'
]

T = TypeVar('T')
_NoneType = type(None)


class ResolutionError(KeyError):
    def __init__(self, typ: Type):
        if inspect.isclass(typ):
            typename = typ.__qualname__
        else:
            typename = str(typ)
        super().__init__(f'Container was not able to resolve type: {typename}')


def _get_return_type(fn: Callable[..., T]) -> Type[T]:
    return get_type_hints(fn)['return']


def _get_type_from_optional(typ: Type[T]) -> Tuple[Type[T], bool]:
    try:
        # Special Optional[T] case, Optional[T] is Union[T, type(None)]
        if (typ.__origin__ is typing.Union
                and len(typ.__args__) == 2
                and typ.__args__[1] is type(None)):
            return typ.__args__[0], True
    except AttributeError:  # no __origin__ / __args__ for non _GenericAlias types
        pass
    return typ, False


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
        if key not in self._spec_dict:
            raise ResolutionError(key)
        return self._spec_dict[key]


class MroStorage(DictStorage):
    def set(self, key: Type[T], spec: 'Spec[T]'):
        actual_type, is_optional = _get_type_from_optional(key)

        if is_optional:
            self.set(actual_type, spec)

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
        key, is_optional = _get_type_from_optional(key)
        try:
            instance = self.get_spec(key).get_instance(self, *args, **kwargs)
            if instance is None and not is_optional:
                raise ResolutionError(key)
            return instance
        except ResolutionError as err:
            if is_optional:
                return None
            else:
                raise err

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
            raise TypeError(f'Instance is not of type {key}')
        spec = InstanceSpec(instance)
        self._storage.set(key, spec)
        return spec

    def register_class(self, cls: Type[T], key: Optional[Type[T]] = None) -> 'ClassSpec[T]':
        key = key or cls
        if not issubclass(cls, key):
            raise TypeError(f'Class {cls} is not a subclass of {key}')
        spec = ClassSpec(cls)
        self._storage.set(key, spec)
        return spec

    def register_singleton_class(self, cls: Type[T],
                                 key: Optional[Type[T]] = None) -> 'SingletonClassSpec[T]':
        key = key or cls
        if not issubclass(cls, key):
            raise TypeError(f'Class {cls} is not a subclass of {key}')
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
        self._arg_spec = inspect.getfullargspec(self._factory)

        if 'return' in self._annotations:
            del self._annotations['return']

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        # Updating kwargs from args
        kwargs.update(zip(self._arg_spec.args, args))

        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs and param_name not in kwargs:
                try:
                    kwargs[param_name] = c.get_instance(param_type)
                except ResolutionError:
                    # Not filling types that container is usable to resolve
                    pass
        kwargs.update(self._kwargs)
        return self._factory(**kwargs)

    def set_kwargs(self, **kwargs):
        self._kwargs = kwargs


class ClassSpec(Spec[T]):
    def __init__(self, cls: Type[T]):
        if not inspect.isclass(cls):
            raise TypeError(f'Expected class type, got {cls} instead')
        self._class = cls
        self._kwargs = {}
        self._arg_spec = inspect.getfullargspec(self._class)

        try:
            # Arg-spec annotations are not forward-ref evaluated, using typing instead
            self._annotations = get_type_hints(self._class.__init__)
            if 'return' in self._annotations:
                del self._annotations['return']
        except AttributeError:  # No __init__ method
            self._annotations = {}

    def get_instance(self, c: Container, *args, **kwargs) -> T:
        # Updating kwargs from args starting from 1 to exclude self
        kwargs.update(zip(self._arg_spec.args[1:], args))

        for param_name, param_type in self._annotations.items():
            if param_name not in kwargs and param_name not in kwargs:
                try:
                    kwargs[param_name] = c.get_instance(param_type)
                except ResolutionError:
                    # Not filling types that container is usable to resolve
                    pass
        kwargs.update(self._kwargs)
        return self._class(**kwargs)

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
