from typing import (
    Iterable,
    Any,
    List,
    Union,
    Generic,
    TypeVar,
    Type,
)
from abc import ABCMeta, abstractmethod
from collections import abc as collections_abc
from functools import lru_cache

from typedi.object_proxy import ObjectProxy
from typedi.typing_utils import (
    get_args,
    get_origin,
    unwrap_decorators,
)

__all__ = [
    "IInstanceResolver",
    "MetaType",
    "ResolutionError",
    "TerminalType",
    "ClassType",
    "NoneTerminalType",
    "GenericTerminalType",
    "UnionType",
    "ListType",
    "IterableType",
    "TupleType",
    "AnyType",
    "python_type_to_meta",
    "type_of",
]


T = TypeVar("T")


class IInstanceResolver(metaclass=ABCMeta):
    @abstractmethod
    def resolve_single_instance(self, type_: "TerminalType[T]") -> T:
        pass

    @abstractmethod
    def iterate_instances(self, type_: "TerminalType[T]") -> Iterable[T]:
        pass

    @abstractmethod
    def iterate_all_instances(self) -> Iterable[Any]:
        pass


class MetaType(Generic[T], metaclass=ABCMeta):
    @abstractmethod
    def can_handle(self, other: "TerminalType[Any]") -> bool:
        pass

    @abstractmethod
    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        pass

    @abstractmethod
    def resolve_single_instance(self, resolver: IInstanceResolver) -> T:
        pass

    @abstractmethod
    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[T]:
        pass


class ResolutionError(TypeError):
    def __init__(self, type_: MetaType[Any]):
        super().__init__(
            f"Container is not able to resolve type '{type_}'. "
            f"Make sure it is registered in the container."
        )


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

    def __hash__(self) -> int:
        return hash("NoneTerminalType")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NoneTerminalType)


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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UnionType) and other.types == self.types


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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ListType) and other.type == self.type


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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IterableType) and self.type == other.type


class TupleType(TerminalType[Any], MetaType[Any]):
    __slots__ = "args"

    def __init__(self, *args: MetaType[Any]):
        self.args = args

    def can_handle(self, other: "TerminalType[Any]") -> bool:
        return isinstance(other, TupleType) and self.args == other.args

    def type_check_object(self, obj: object) -> bool:
        if isinstance(obj, tuple) and len(obj) == len(self.args):
            for arg_type, arg_value in zip(self.args, obj):
                if not arg_type.type_check_object(arg_value):
                    return False
            return True
        return False

    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        for arg in self.args:
            yield from arg.iterate_possible_terminal_types()
        yield self

    def resolve_single_instance(self, resolver: IInstanceResolver) -> Iterable[Any]:
        try:
            # First, try resolve tuple as terminal.
            # There might be an instance with exact tuple type registered.
            return resolver.resolve_single_instance(self)
        except ResolutionError:
            # Auto-resolve tuple if not present.
            # It is simply instance resolution of separate tuple arguments combined.
            return tuple(arg.resolve_single_instance(resolver) for arg in self.args)

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[Any]:
        return resolver.iterate_instances(self)

    def __str__(self) -> str:
        return f"Tuple[" + ",".join(str(arg) for arg in self.args) + "]"

    def __hash__(self) -> int:
        return hash(self.args)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TupleType) and self.args == other.args


class AnyType(MetaType[Any]):
    def can_handle(self, other: "TerminalType[Any]") -> bool:
        return True

    def iterate_possible_terminal_types(self) -> Iterable["TerminalType[Any]"]:
        return ()  # Special case

    def resolve_single_instance(self, resolver: IInstanceResolver) -> Iterable[Any]:
        for instance in resolver.iterate_all_instances():
            return instance
        raise ResolutionError(self)

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[Any]:
        return resolver.iterate_all_instances()

    def __str__(self) -> str:
        return f"Any"

    def __hash__(self) -> int:
        return hash("AnyType")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AnyType)


@lru_cache(1024)
def python_type_to_meta(type_: Type[T]) -> MetaType[T]:
    """Converts python types to custom type-system

    For collection base classes see:
    https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes

    :param type_: any python type
    :return: MetaType
    """
    type_ = unwrap_decorators(type_)

    if type_ is type(None):
        return NoneTerminalType()  # type: ignore

    if isinstance(type_, type):
        return ClassType[T](type_)

    if type_ is Any:
        return AnyType()

    # Generics
    origin = get_origin(type_)
    args = get_args(type_)

    if origin is not None and args:
        if origin == Union:
            if len(args) == 1:
                # Only 1 arg, no need for union
                return python_type_to_meta(args[0])
            return UnionType(*(python_type_to_meta(t) for t in args))

        if origin is tuple:
            return TupleType(*(python_type_to_meta(t) for t in args))

        if issubclass(origin, collections_abc.Sequence):
            return ListType(python_type_to_meta(args[0]))

        if issubclass(origin, collections_abc.Iterable):
            return IterableType(python_type_to_meta(args[0]))

        if origin is type:
            return GenericTerminalType(type_)

    raise TypeError(f"Unsupported type {type_}")


def type_of(obj: object) -> MetaType[Any]:
    t = type(obj)

    if t is tuple:
        if not obj:
            return ClassType(tuple)

        return TupleType(*(type_of(arg) for arg in obj))

    if t is list:
        if not obj:
            return ClassType(list)

        types = set()
        for arg in obj:
            types.add(type_of(arg))

        if len(types) == 1:
            one_type = next(iter(types))
            return ListType(one_type)
        return ListType(UnionType(*types))

    return python_type_to_meta(type(obj))
