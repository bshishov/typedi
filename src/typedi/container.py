from typing import (
    Iterable,
    Any,
    Dict,
    List,
    Union,
    Generic,
    TypeVar,
    Callable,
    Optional,
    Tuple,
    Type,
)
from abc import ABCMeta, abstractmethod
from collections import defaultdict, abc as collections_abc
import inspect

from typedi.object_proxy import ObjectProxy
from typedi.typing_utils import (
    get_return_type,
    type_forward_ref_scope,
    eval_type,
    ForwardRef,
    get_origin,
    unwrap_decorators,
)

__all__ = ["Container", "ResolutionError"]


T = TypeVar("T")


class IInstanceResolver:
    def resolve_single_instance(self, type_: "TerminalType[T]") -> T:
        raise NotImplementedError

    def iterate_instances(self, type_: "TerminalType[T]") -> Iterable[T]:
        raise NotImplementedError


class MetaType(Generic[T]):
    def can_handle(self, other: "TerminalType[Any]") -> bool:
        raise NotImplemented

    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        raise NotImplemented

    def resolve_single_instance(self, resolver: IInstanceResolver) -> T:
        raise NotImplementedError

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[T]:
        raise NotImplementedError


class TerminalType(Generic[T], MetaType[T], metaclass=ABCMeta):
    """The type that cannot be further decomposed.

    Example: int, object, SomeClass, Type[SomeClass]
    """

    @abstractmethod
    def type_check_object(self, obj: object) -> bool:
        pass


_TObject = TypeVar("_TObject", bound=object)


class ClassType(Generic[_TObject], TerminalType[_TObject]):
    """Classes"""

    __slots__ = "type"

    def __init__(self, type_: Type[_TObject]):
        assert isinstance(type_, type)
        self.type = type_

    def type_check_object(self, obj: object) -> bool:
        if type(obj) == ObjectProxy:
            return True
        return isinstance(obj, self.type)

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        if isinstance(other, ClassType):
            return issubclass(other.type, self.type)
        return False

    def iterate_possible_terminal_types(self) -> Iterable["ClassType[Any]"]:
        for base in self.type.__mro__[:-1]:
            yield ClassType[Any](base)

    def resolve_single_instance(self, resolver: IInstanceResolver) -> _TObject:
        return resolver.resolve_single_instance(self)

    def iterate_resolved_instances(
        self, resolver: IInstanceResolver
    ) -> Iterable[_TObject]:
        return resolver.iterate_instances(self)

    def __str__(self) -> str:
        return self.type.__qualname__

    def __hash__(self) -> int:
        return hash(self.type)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ClassType) and self.type == other.type


class NoneTerminalType(TerminalType[None]):
    def iterate_possible_terminal_types(self) -> Iterable["NoneTerminalType"]:
        yield self

    def type_check_object(self, obj: object) -> bool:
        return obj is None

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        return isinstance(other, NoneTerminalType)

    def resolve_single_instance(self, resolver: IInstanceResolver) -> None:
        return None

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[None]:
        yield None


class GenericTerminalType(TerminalType[Any]):
    __slots__ = "type"

    def __init__(self, type_: Type[Any]):
        self.type = type_

    def iterate_possible_terminal_types(self) -> Iterable["GenericTerminalType"]:
        yield self

    def type_check_object(self, obj: object) -> bool:
        # Naive optimistic resolution
        return isinstance(obj, get_origin(self.type))

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        return isinstance(other, GenericTerminalType) and self.type == other.type

    def resolve_single_instance(self, resolver: IInstanceResolver) -> object:
        return resolver.resolve_single_instance(self)

    def iterate_resolved_instances(
        self, resolver: IInstanceResolver
    ) -> Iterable[object]:
        return resolver.iterate_instances(self)

    def __str__(self) -> str:
        return str(self.type)

    def __hash__(self) -> int:
        return hash(self.type)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GenericTerminalType) and self.type == other.type


class UnionType(Generic[T], MetaType[T]):
    __slots__ = "types"

    def __init__(self, *types: MetaType[T]) -> None:
        self.types = types

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        for t in self.types:
            if t.can_handle(other):
                return True
        return False

    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        for t in self.types:
            for possible in t.iterate_possible_terminal_types():
                yield possible

    def resolve_single_instance(self, resolver: IInstanceResolver) -> T:
        for t in self.types:
            try:
                return t.resolve_single_instance(resolver)
            except ResolutionError:
                pass

        raise ResolutionError(self)

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[T]:
        for t in self.types:
            yield from t.iterate_resolved_instances(resolver)

    def __str__(self) -> str:
        return "Union[" + ", ".join(str(t) for t in self.types) + "]"


class ListType(Generic[T], MetaType[List[T]]):
    __slots__ = "type"

    def __init__(self, type_: MetaType[T]) -> None:
        self.type = type_

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        return self.type.can_handle(other)

    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        return self.type.iterate_possible_terminal_types()

    def resolve_single_instance(self, resolver: IInstanceResolver) -> List[T]:
        return list(self.type.iterate_resolved_instances(resolver))

    def iterate_resolved_instances(
        self, resolver: IInstanceResolver
    ) -> Iterable[List[T]]:
        yield list(self.type.iterate_resolved_instances(resolver))

    def __str__(self) -> str:
        return f"List[{self.type}]"


class IterableType(Generic[T], MetaType[Iterable[T]]):
    __slots__ = "type"

    def __init__(self, type_: MetaType[T]) -> None:
        self.type = type_

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        return self.type.can_handle(other)

    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        return self.type.iterate_possible_terminal_types()

    def resolve_single_instance(self, resolver: IInstanceResolver) -> Iterable[T]:
        return self.type.iterate_resolved_instances(resolver)

    def iterate_resolved_instances(
        self, resolver: IInstanceResolver
    ) -> Iterable[Iterable[T]]:
        yield self.type.iterate_resolved_instances(resolver)

    def __str__(self) -> str:
        return f"List[{self.type}]"


def python_type_to_meta(type_: Type[T]) -> MetaType[T]:
    type_ = unwrap_decorators(type_)

    if type_ is type(None):
        return NoneTerminalType()  # type: ignore

    if isinstance(type_, type):
        return ClassType[T](type_)

    if hasattr(type_, "__origin__"):
        origin = type_.__origin__
        if origin == Union:
            return UnionType(*(python_type_to_meta(t) for t in type_.__args__))

        if issubclass(origin, collections_abc.Sequence):
            return ListType(python_type_to_meta(type_.__args__[0]))

        if issubclass(origin, collections_abc.Iterable):
            return IterableType(python_type_to_meta(type_.__args__[0]))

        # Other generics
        return GenericTerminalType(type_)

    raise TypeError(f"Unresolvable type {type_}")


class CachedStorage:
    def __init__(self) -> None:
        self.providers_index: Dict[
            TerminalType[Any], List["InstanceProvider[Any]"]
        ] = defaultdict(list)

    def add(self, provider: "InstanceProvider[Any]") -> None:
        for just_type in provider.get_type().iterate_possible_terminal_types():
            self.providers_index[just_type].append(provider)

    def query(self, type_: TerminalType[T]) -> Iterable["InstanceProvider[T]"]:
        for provider in reversed(self.providers_index[type_]):
            yield provider


class InstanceResolver(IInstanceResolver):
    __slots__ = "storage", "container"

    def __init__(self, storage: CachedStorage, container: "Container") -> None:
        self.storage = storage
        self.container = container

    def resolve_single_instance(self, type_: "TerminalType[T]") -> T:
        for instance in self.iterate_instances(type_):
            return instance
        raise ResolutionError(type_)

    def iterate_instances(self, type_: "TerminalType[T]") -> Iterable[T]:
        for provider in self.storage.query(type_):
            instance_or_iterable = provider.get_instance(self.container)
            for item in filter_instances_of_terminal_type(instance_or_iterable, type_):
                yield item


def filter_instances_of_terminal_type(
    obj: object, type_: TerminalType[T]
) -> Iterable[T]:
    if type_.type_check_object(obj):
        yield obj  # type: ignore
    elif hasattr(obj, "__iter__"):
        for item in obj:  # type: ignore
            yield from filter_instances_of_terminal_type(item, type_)


class ResolutionError(TypeError):
    def __init__(self, t: MetaType[Any]):
        super().__init__(f"Container is not able to resolve type: {t}")


class Container:
    __slots__ = "_storage"

    def __init__(self) -> None:
        self._storage = CachedStorage()

        # Register self, so that client code can access the instance of a container
        self.register_instance(self)

    def register_instance(self, instance: object) -> None:
        self._storage.add(ConstInstanceProvider(instance))

    def register_factory(self, factory: Callable[..., Any]) -> None:
        self._storage.add(FactoryInstanceProvider(factory))

    def register_class(self, cls: type) -> None:
        self.register_factory(cls)

    def register_singleton_factory(self, factory: Callable[..., Any]) -> None:
        self._storage.add(SingletonInstanceProvider(FactoryInstanceProvider(factory)))

    def register_singleton_class(self, cls: type) -> None:
        self.register_singleton_factory(cls)

    def resolve(self, type_: Type[T]) -> T:
        meta_type = python_type_to_meta(type_)
        return meta_type.resolve_single_instance(InstanceResolver(self._storage, self))

    def get_all_instances(self, type_: Type[T]) -> List[T]:
        meta_type = python_type_to_meta(type_)
        return list(
            meta_type.iterate_resolved_instances(InstanceResolver(self._storage, self))
        )

    def iter_all_instances(self, type_: Type[T]) -> Iterable[T]:
        meta_type = python_type_to_meta(type_)
        return meta_type.iterate_resolved_instances(
            InstanceResolver(self._storage, self)
        )


class InstanceProvider(Generic[T], metaclass=ABCMeta):
    @abstractmethod
    def get_instance(self, container: Container) -> T:
        pass

    @abstractmethod
    def get_type(self) -> MetaType[T]:
        pass


class ConstInstanceProvider(InstanceProvider[T]):
    __slots__ = "_instance"

    def __init__(self, instance: T):
        self._instance = instance

    def get_instance(self, container: Container) -> T:
        return self._instance

    def get_type(self) -> MetaType[T]:
        return ClassType[T](type(self._instance))


class FactoryInstanceProvider(InstanceProvider[T]):
    __slots__ = "_factory", "_annotations", "_eval_scope", "_proxy_recursion_guard"

    def __init__(self, factory: Callable[..., T]):
        self._factory = factory
        self._annotations = self._build_annotations()
        self._eval_scope = type_forward_ref_scope(get_return_type(factory))
        self._proxy_recursion_guard: Optional[ObjectProxy] = None

    def get_type(self) -> MetaType[T]:
        return python_type_to_meta(get_return_type(self._factory))

    def _build_annotations(self) -> Dict[str, Tuple[Any, bool, bool]]:
        annotations = {}

        signature = inspect.signature(self._factory)

        for param_name, param in signature.parameters.items():
            param_annotation = param.annotation
            has_default = param.default is not inspect.Parameter.empty
            is_var_positional = param.kind == inspect.Parameter.VAR_POSITIONAL

            # **kwargs are not supported. They are assumed to be optional by design.
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

    def _get_instance(self, container: Container) -> T:
        args: Tuple[Any, ...] = tuple()
        kwargs = {}

        for param_name, (
            param_annotation,
            is_var_positional,
            has_default,
        ) in self._annotations.items():
            # ForwardRef evaluation for module-level declarations in the same module as the user class
            param_annotation = eval_type(param_annotation, globals(), self._eval_scope)

            try:
                if is_var_positional:
                    args = tuple(container.iter_all_instances(param_annotation))
                else:
                    kwargs[param_name] = container.resolve(param_annotation)
            except ResolutionError:
                if not has_default:
                    # There is no default for this parameter and container was unable to resolve the type.
                    # Which means that it is not possible to construct the instance.
                    # So, just re-raising the exception.
                    raise

        return self._factory(*args, **kwargs)

    def get_instance(self, container: Container) -> T:
        # Resolution of the type might be recursive.
        # Instead of completely preventing recursive and circular references
        # we substitute the object with its uninitialized proxy.
        # Consider this trickery as late object initialization.

        # If the proxy is available (i.e. recursive call)
        # return the proxy.
        # By doing this we prevent infinite recursion of get_instance() calls
        if self._proxy_recursion_guard is not None:
            return self._proxy_recursion_guard  # type: ignore

        # First - construct uninitialized proxy.
        # __init__ is not called on purpose - it will make actual object
        # unusable until it is completely initialized.
        self._proxy_recursion_guard = ObjectProxy.__new__(ObjectProxy)
        try:
            # Actual instance creation proxies aside
            instance = self._get_instance(container)

            # Since we have an instance - initialize the proxy
            # by actual instance.
            # This will make proxy completely mimic actual instance.
            self._proxy_recursion_guard.__init__(instance)

            # This is a `true` get_instance call - return actual unproxied instance
            return instance
        finally:
            # After instance is successfully created or an exception occurred
            # Clear the guard so that next call won't utilize this proxy
            self._proxy_recursion_guard = None


class SingletonInstanceProvider(InstanceProvider[T]):
    __slots__ = "_provider", "_instance"

    def __init__(self, provider: InstanceProvider[T]):
        self._provider = provider
        self._instance: Union[T, None] = None

    def get_instance(self, container: Container) -> T:
        if self._instance is None:
            self._instance = self._provider.get_instance(container)
        return self._instance

    def get_type(self) -> MetaType[T]:
        return self._provider.get_type()
