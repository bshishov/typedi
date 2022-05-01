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
    Mapping,
)
import typing
import sys
import inspect
import warnings
from collections import defaultdict, abc as collection_abc
from abc import ABCMeta, abstractmethod
from functools import partial, partialmethod
from itertools import chain


__all__ = [
    "MroStorage",
    "Container",
    "ResolutionError",
]

T = TypeVar("T")


# Dynamic forward ref imports / declarations
# 3.6  : https://github.com/python/cpython/blob/3.6/Lib/typing.py#L216
# 3.7  : https://github.com/python/cpython/blob/3.7/Lib/typing.py#L438
# 3.8  : https://github.com/python/cpython/blob/3.8/Lib/typing.py#L489
# 3.9  : https://github.com/python/cpython/blob/3.9/Lib/typing.py#L516
# 3.10 : https://github.com/python/cpython/blob/3.10/Lib/typing.py#L653
if sys.version_info >= (3, 7):
    ForwardRef = getattr(typing, "ForwardRef")
elif sys.version_info >= (3, 5):
    ForwardRef = getattr(typing, "_ForwardRef")
else:
    raise ImportError("typing.ForwardRef is not supported")


# Evaluates meta types recursively including ForwardRef
# 3.6  : https://github.com/python/cpython/blob/3.6/Lib/typing.py#L348
# 3.7  : https://github.com/python/cpython/blob/3.7/Lib/typing.py#L258
# 3.8  : https://github.com/python/cpython/blob/3.8/Lib/typing.py#L265
# 3.9  : https://github.com/python/cpython/blob/3.9/Lib/typing.py#L285
# 3.10 : https://github.com/python/cpython/blob/3.10/Lib/typing.py#L319
_eval_type = getattr(typing, "_eval_type")


class ResolutionError(KeyError):
    def __init__(self, typ: Any):
        if isinstance(typ, type):
            typename = typ.__qualname__
        else:
            typename = str(typ)
        super().__init__(f"Container is not able to resolve type: {typename}")


def _unwrap_decorators(o: Any) -> Any:
    """Unwraps decorators to get actual decorated class or function
    Note: don't forget @functools.wraps() around your decorators
    """
    while hasattr(o, "__wrapped__"):
        o = o.__wrapped__
    return o


def _return_type(obj: Union[Type[T], Callable[..., T]]) -> Union[Type[T], type]:
    """Returns the actual type, being produced by type or callable.

    It handles decorators, partials, ForwardRefs and their combinations.
    """
    obj = _unwrap_decorators(obj)

    if isinstance(obj, type):
        # Classes produce themselves
        return obj

    # Partial is an object of class "functools.partial"
    # So we need to resolve return type from the wrapped function
    if isinstance(obj, (partial, partialmethod)):
        return _return_type(obj.func)

    # Functions and methods
    try:
        callable_type_hints = get_type_hints(obj)
    except TypeError:  # not a function/method
        callable_type_hints = get_type_hints(obj.__call__)  # type: ignore

    return_type: Union[Type[T], type, None] = callable_type_hints.get("return")

    if return_type is None:
        raise TypeError(f"Missing return type annotation for {obj}")
    return return_type


def _type_forward_ref_scope(
    type_: Union[Type[T], Callable[..., T]]
) -> Mapping[str, Any]:
    """Returns dict scope for ForwardRef evaluation for use in _eval_type
    Right now only module-level ForwardRefs are supported.

    Note: this function does not unwrap decorators (it is done outside)
    TODO: make it work for base-classes (MRO hierarchy)

    Reference https://github.com/python/cpython/blob/3.10/Lib/typing.py#L1808
    :param type_: any type
    :return: Dictionary containing globals to resolve ForwardRef of annotations of type_
    """
    if isinstance(type_, type):
        # Scope of a type is module's dict (in most cases).
        # It is difficult to get scope from locally defined classes
        # thus this functionality is omitted for simplicity.
        return getattr(sys.modules.get(type_.__module__, None), "__dict__", {})

    return getattr(type_, "__globals__", {})


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
    """Storage of InstanceProviders (factories) indexed by its production type.

    For each production type there might be multiple (unique) instance providers.
    """

    __slots__ = "_instance_providers"

    def __init__(self) -> None:
        self._instance_providers: Dict[
            Type[Any], List[InstanceProvider[Any]]
        ] = defaultdict(list)
        self._instance_providers[type(None)] = [ConstInstanceProvider(None)]

    def add(self, type_: Type[T], provider: "InstanceProvider[T]") -> None:
        """Adds new InstanceProvider to index"""
        if isinstance(type_, type):
            # To support inheritance queries we build index by
            # adding all the base classes of the type to index.
            # Except for the `object` which is last in the MRO.
            for base in type_.__mro__[:-1]:
                if provider not in self._instance_providers[base]:
                    self._instance_providers[base].append(provider)
        elif _get_origin(type_) == Union:
            # If the production type is a union type
            # then provider might produce different results in different cases.
            # Adding provider to index for each option separately
            for arg in _get_args(type_):
                self.add(arg, provider)
        else:
            # All other cases (generics and special types) are indexed as-is
            if provider not in self._instance_providers[type_]:
                self._instance_providers[type_].append(provider)

    def query(self, query: Type[T]) -> Iterable["InstanceProvider[T]"]:
        """Queries all InstanceProviders that can (potentially) provide an instance
        that matches type query. Newly added providers returned first"""
        return reversed(self._instance_providers[query])


class Container:
    __slots__ = "_storage"

    def __init__(self, storage: Optional[MroStorage] = None):
        self._storage = storage or MroStorage()

        # Register self, so that client code can access the instance of a container
        self.register_instance(self)

    def _resolve_all_instances(
        self, query: Type[T], used_providers: Set["InstanceProvider[T]"]
    ) -> Iterable[T]:
        """Main resolution method."""

        # Decorated classes might be used as a query
        query = _unwrap_decorators(query)

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

    def get_instance(self, query: Type[T]) -> T:
        warnings.warn(
            ".get_instance() is deprecated, use .resolve()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.resolve(query)

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
    __slots__ = "_factory", "_annotations", "_eval_scope"

    def __init__(self, factory: Callable[..., T]):
        self._factory = factory
        self._annotations = self._build_annotations()
        self._eval_scope = _type_forward_ref_scope(_return_type(factory))

    def _build_annotations(self) -> Dict[str, Tuple[Any, bool, bool]]:
        annotations = {}

        signature = inspect.signature(self._factory)

        for param_name, param in signature.parameters.items():
            param_annotation = param.annotation
            has_default = param.default is not inspect.Parameter.empty
            is_var_positional = param.kind == inspect.Parameter.VAR_POSITIONAL

            # **kwargs are not supported. They are assumed to be optional by desing.
            # So we can just skip resolution
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            if param_annotation is inspect.Parameter.empty:
                if not has_default:
                    raise TypeError(
                        f"Missing annotation (or default) for parameter '{param_name}' of {self._factory}. "
                        f"Container won't be able to resolve this type."
                    )
            else:
                # If param_annotation is a string - it is (in most cases) a ForwardRef.
                # So performing explicit conversion ForwardRef for _eval_type to evaluate it later
                if isinstance(param_annotation, str):
                    param_annotation = ForwardRef(param_annotation)

                annotations[param_name] = (
                    param_annotation,
                    is_var_positional,
                    has_default,
                )
        return annotations

    def get_instance(self, container: Container) -> T:
        kwargs = {}
        args: Optional[Tuple[Any, ...]] = None

        for param_name, (
            param_annotation,
            is_var_positional,
            has_default,
        ) in self._annotations.items():
            # ForwardRef evaluation for module-level declarations in the same module as the user class
            param_annotation = _eval_type(param_annotation, globals(), self._eval_scope)

            try:
                if is_var_positional:
                    args = tuple(container.iter_all_instances(param_annotation))
                else:
                    kwargs[param_name] = container.resolve(param_annotation)
            except ResolutionError:
                if not has_default:
                    # There is no default for this parameter and container was unable to resolve the type.
                    # Which means that it is not possible to construct the instance.
                    # So, just re-raising the exception
                    raise

        if args:
            return self._factory(*args, **kwargs)

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
