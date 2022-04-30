from typing import (
    Optional,
    Type,
    Callable,
    Dict,
    get_type_hints,
    TypeVar,
    Generic,
    Iterable,
    List,
    Any,
    Union,
    Set,
    Tuple,
)
import inspect
from collections import defaultdict, abc as collection_abc
from abc import ABCMeta, abstractmethod
from functools import partial


__all__ = [
    "MroStorage",
    "Container",
    "ResolutionError",
]

T = TypeVar("T")


class ResolutionError(KeyError):
    def __init__(self, typ: Any):
        if isinstance(typ, type):
            typename = typ.__qualname__
        else:
            typename = str(typ)
        super().__init__(f"Container is not able to resolve type: {typename}")


def _return_type(obj: Union[Type[T], Callable[..., T]]) -> Union[Type[T], type]:
    if isinstance(obj, type):
        # Classes or types produce themselves
        return obj

    # Partial is an object of class "functools.partial"
    # So we need to resolve return type from the wrapped function
    if isinstance(obj, partial):
        return _return_type(obj.func)

    # Functions and methods
    return_type: Union[Type[T], type, None] = get_type_hints(obj).get("return")
    if return_type is None:
        raise TypeError(f"Missing return type annotation for {obj}")
    return return_type


def _matches_query(obj: Any, query: Any) -> bool:
    # Note: not taking Union into account
    # because it is already resolved in Container._resolve_all_instances
    if isinstance(query, type):
        return isinstance(obj, query)

    if _get_origin(query) == type(obj):
        # Optimistic Generic check
        return True

    return False


def _get_origin(type_: Any) -> Any:
    """Get unsubscribed version of `type_`.
    Examples:
        _get_origin(int) is None
        _get_origin(typing.Any) is None
        _get_origin(typing.List[int]) is list
        _get_origin(typing.Literal[123]) is typing.Literal
        _get_origin(typing.Generic[T]) is typing.Generic
        _get_origin(typing.Generic) is typing.Generic
        _get_origin(typing.Annotated[int, "some"]) is int

    NOTE: This method intentionally allows Annotated to proxy __origin__
    """
    if type_ is Generic:  # Special case
        return type_
    return getattr(type_, "__origin__", None)


def _get_args(type_: Any) -> Tuple[Any, ...]:
    """Get type arguments with all substitutions performed.
    For unions, basic simplifications used by Union constructor are performed.

    Examples:
        _get_args(Dict[str, int]) == (str, int)
        _get_args(int) == ()
        _get_args(Union[int, Union[T, int], str][int]) == (int, str)
        _get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
        _get_args(Callable[[], T][int]) == ([], int)
    """
    return getattr(type_, "__args__", tuple())


def _is_subclass(left: Any, right: type) -> bool:
    """Modified `issubclass` to support generics and other types.
    __origin__ is being tested for generics
    right value should be a class
    Examples:

        _is_subclass(typing.List[int], collections.abc.Sequence) == True
        _is_subclass(typing.List, collections.abc.Sequence) == True
        _is_subclass(typing.Tuple, collections.abc.Sequence) == True
        _is_subclass(typing.Any, collections.abc.Sequence) == False
        _is_subclass(int, collections.abc.Sequence) == False
    """
    try:
        return issubclass(getattr(left, "__origin__", left), right)
    except TypeError:
        return False


class MroStorage:
    __slots__ = "_instance_providers"

    def __init__(self) -> None:
        self._instance_providers: Dict[
            Type[Any], List[InstanceProvider[Any]]
        ] = defaultdict(list)
        self._instance_providers[type(None)] = [ConstInstanceProvider(None)]

    def add(self, type_: Type[T], provider: "InstanceProvider[T]") -> None:
        if isinstance(type_, type):
            # To support inheritance queries we build index by
            # adding all the base classes of the type except object
            # which is last in the MRO
            for base in type_.__mro__[:-1]:
                if provider not in self._instance_providers[base]:
                    self._instance_providers[base].insert(0, provider)
        elif _get_origin(type_) == Union:
            # If the production type is a union type
            # which means that provider might produce
            # different results in different cases
            # we need to index each option separately
            for arg in _get_args(type_):
                self.add(arg, provider)
        else:
            # All other cases (generics and special types) are indexed as-is
            if provider not in self._instance_providers[type_]:
                self._instance_providers[type_].insert(0, provider)

    def query(self, query: Type[T]) -> Iterable["InstanceProvider[T]"]:
        yield from self._instance_providers[query]


class Container:
    __slots__ = "_storage"

    def __init__(self, storage: Optional[MroStorage] = None):
        self._storage = storage or MroStorage()

        # Register self, so that client code can access the instance of a container
        # that has provided dependencies during instance resolving (if requested)
        self.register_instance(self)

    def _resolve_all_instances(
        self, query: Type[T], used_providers: Set["InstanceProvider[T]"]
    ) -> Iterable[T]:
        # Try resolve direct query match using container
        for provider in self._storage.query(query):
            if provider not in used_providers:
                instance = provider.get_instance(self)

                # instance is not guaranteed to match query
                # i.e. `provider` is f() -> A | B  while `query` could be B | C
                if _matches_query(instance, query):
                    yield instance
                    used_providers.add(provider)

        # Try break down complex query
        type_origin = _get_origin(query)
        if type_origin:
            type_args = _get_args(query)
            if type_origin == Union:
                # Union resolution - try resolve by each
                for arg in type_args:
                    yield from self._resolve_all_instances(arg, used_providers)
            elif _is_subclass(type_origin, collection_abc.Sequence):
                # Sequence query resolution
                if len(type_args) == 1:
                    yield list(
                        self._resolve_all_instances(type_args[0], used_providers)
                    )  # type: ignore
            elif type_origin is collection_abc.Iterable:
                # Iterable query resolution
                if len(type_args) == 1:
                    # Note: yielding iterator intentionally
                    yield self._resolve_all_instances(type_args[0], used_providers)  # type: ignore

    def resolve(self, query: Type[T]) -> T:
        """Resolves instance (or collection of instances) of specified query

        Examples:

            resolve(A)
                Will find the latest registered instance of type A
                or raise ResolutionError if resolution is not possible

            resolve(Union[A, B])
                Will find instance of either type A or B
                (resolution performs left to right)
                or raise ResolutionError if resolution is not possible

            resolve(Optional[A])
                Same as resolve(Union[A, None])
                Will try to find the latest registered instance of type A
                or return None (a valid instance of type(None))

            resolve(List[A])
                Will resolve into a list by performing resolution of A.
                If there are no instances of A returns an empty list.

            resolve(Iterable[A])
                Will resolve into an iterator by performing resolution of A.
                If there are no instances of A returns an empty iterable.

        :param query: Query to resolve.
        :raises ResolutionError: When container is unable to resolve the query
        :returns: Resolved instance or collection
        """
        for instance in self._resolve_all_instances(query, set()):
            return instance

        raise ResolutionError(query)

    def iter_all_instances(self, query: Type[T]) -> Iterable[T]:
        return self._resolve_all_instances(query, set())

    def get_all_instances(self, query: Type[T]) -> List[T]:
        return list(self._resolve_all_instances(query, set()))

    def register_instance(self, instance: object) -> None:
        self._storage.add(type(instance), ConstInstanceProvider(instance))

    def register_class(self, cls: Type[T]) -> None:
        # Classes are factories of objects
        return self.register_factory(cls)

    def register_singleton_class(self, cls: Type[T]) -> None:
        # Classes are factories of objects
        return self.register_singleton_factory(cls)

    def register_factory(self, factory: Callable[..., T]) -> None:
        return_type = _return_type(factory)
        self._storage.add(return_type, FactoryInstanceProvider(factory))

    def register_singleton_factory(self, factory: Callable[..., T]) -> None:
        return_type = _return_type(factory)
        self._storage.add(
            return_type, SingletonInstanceProvider(FactoryInstanceProvider(factory))
        )


class InstanceProvider(Generic[T], metaclass=ABCMeta):
    @abstractmethod
    def get_instance(self, container: Container) -> T:
        pass


class ConstInstanceProvider(InstanceProvider[T]):
    __slots__ = "_instance"

    def __init__(self, instance: T):
        self._instance = instance

    def get_instance(self, container: Container) -> T:
        return self._instance


class FactoryInstanceProvider(InstanceProvider[T]):
    __slots__ = "_factory", "_signature"

    def __init__(self, factory: Callable[..., T]):
        self._factory = factory
        self._signature = inspect.signature(self._factory)

    def get_instance(self, container: Container) -> T:
        kwargs = {}

        for param_name, param in self._signature.parameters.items():
            param_annotation = param.annotation
            if param_annotation is inspect.Parameter.empty:
                # Not filling parameters with empty annotations
                continue

            try:
                kwargs[param_name] = container.resolve(param_annotation)
            except ResolutionError:
                # Not filling parameters that container is unable to resolve
                continue

        return self._factory(**kwargs)


class SingletonInstanceProvider(InstanceProvider[T]):
    __slots__ = "_provider", "_instance"

    def __init__(self, provider: InstanceProvider[T]):
        self._provider = provider
        self._instance: Optional[T] = None

    def get_instance(self, container: Container) -> T:
        if self._instance is None:
            self._instance = self._provider.get_instance(container)
        return self._instance
