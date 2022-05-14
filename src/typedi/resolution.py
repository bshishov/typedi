from typing import Iterable, Any, List, Union, Generic, TypeVar, Type
import sys
from abc import ABCMeta, abstractmethod
from collections import abc as collections_abc
from functools import lru_cache
from itertools import product

from typedi.object_proxy import ObjectProxy
from typedi.typing_utils import (
    get_args,
    get_origin,
    unwrap_decorators,
)

__all__ = [
    "IInstanceResolver",
    "BaseType",
    "ResolutionError",
    "ClassType",
    "NoneType",
    "TypeOfType",
    "UnionType",
    "ListType",
    "IterableType",
    "TupleType",
    "AnyType",
    "intersects",
    "as_type",
    "type_of",
    "NONE_TYPE",
    "ANY_TYPE",
]

if sys.version_info >= (3, 8):
    __all__.append("ProtocolType")


T = TypeVar("T")


class IInstanceResolver(metaclass=ABCMeta):
    @abstractmethod
    def resolve_single_instance(self, type_: "BaseType[T]") -> T:
        pass

    @abstractmethod
    def iterate_instances(self, type_: "BaseType[T]") -> Iterable[T]:
        pass


class BaseType(Generic[T], metaclass=ABCMeta):
    @abstractmethod
    def contains(self, other: "BaseType[Any]") -> bool:
        pass

    @abstractmethod
    def resolves(self, other: "BaseType[Any]") -> bool:
        pass

    @abstractmethod
    def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
        pass

    @abstractmethod
    def resolve_single_instance(self, resolver: IInstanceResolver) -> T:
        pass

    @abstractmethod
    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[T]:
        pass

    @abstractmethod
    def accepts_resolved_object(self, obj: object) -> bool:
        pass


class ResolutionError(TypeError):
    def __init__(self, type_: BaseType[Any]):
        super().__init__(
            f"Container is not able to resolve type '{type_}'. "
            f"Make sure it is registered in the container."
        )


_TObject = TypeVar("_TObject", bound=object)


class ClassType(Generic[_TObject], BaseType[_TObject]):
    __slots__ = "type"

    def __init__(self, type_: Type[_TObject]):
        assert isinstance(type_, type)
        self.type = type_

    def accepts_resolved_object(self, obj: object) -> bool:
        if type(obj) == ObjectProxy:
            return True
        return isinstance(obj, self.type)

    def contains(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, ClassType) and issubclass(other.type, self.type)

    def resolves(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, ClassType) and issubclass(other.type, self.type)

    def iterate_terminal_resolvable_types(self) -> Iterable["ClassType[Any]"]:
        return (self,)

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

    def __repr__(self):
        return f"{self.__class__.__name__}({self.type!r})"


class NoneType(BaseType[None]):
    def iterate_terminal_resolvable_types(self) -> Iterable["NoneType"]:
        return (self,)

    def accepts_resolved_object(self, obj: object) -> bool:
        return obj is None

    def contains(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, NoneType)

    def resolves(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, NoneType)

    def resolve_single_instance(self, resolver: IInstanceResolver) -> None:
        return None

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[None]:
        return (None,)

    def __hash__(self) -> int:
        return hash("NoneTerminalType")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NoneType)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class TypeOfType(BaseType[Any]):
    __slots__ = "type"

    def __init__(self, type_: BaseType[Any]):
        self.type = type_

    def iterate_terminal_resolvable_types(self) -> Iterable["TypeOfType"]:
        return (self,)

    def accepts_resolved_object(self, obj: object) -> bool:
        try:
            type_ = as_type(obj)
        except TypeError:
            return False

        return self.type.contains(type_)

    def contains(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, TypeOfType) and self.type.contains(other.type)

    def resolves(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, TypeOfType) and self.type.contains(other.type)

    def resolve_single_instance(self, resolver: IInstanceResolver) -> object:
        return resolver.resolve_single_instance(self)

    def iterate_resolved_instances(
        self, resolver: IInstanceResolver
    ) -> Iterable[object]:
        return resolver.iterate_instances(self)

    def __str__(self) -> str:
        return f"Type[{self.type}]"

    def __hash__(self) -> int:
        return hash(("TypeOfType", self.type))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TypeOfType) and self.type == other.type

    def __repr__(self):
        return f"{self.__class__.__name__}({self.type!r})"


class UnionType(Generic[T], BaseType[T]):
    __slots__ = "types", "types_set"

    def __init__(self, *types: BaseType[T]) -> None:
        self.types = types

        # duplicated storage for hashing and comparison
        self.types_set = set(types)

    def contains(self, other: "BaseType[Any]") -> bool:
        if isinstance(other, UnionType):
            # TODO: Implement
            raise NotImplementedError(
                "Union vs Union subtype check is not implemented yet"
            )
        return any(t.contains(other) for t in self.types)

    def resolves(self, other: "BaseType[Any]") -> bool:
        return any(t.resolves(other) for t in self.types)

    def accepts_resolved_object(self, obj: object) -> bool:
        return any(t.accepts_resolved_object(obj) for t in self.types)

    def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
        for t in self.types:
            yield from t.iterate_terminal_resolvable_types()

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

    def __hash__(self):
        return hash(("UnionType", self.types_set))

    def __str__(self) -> str:
        return "Union[" + ", ".join(str(t) for t in self.types) + "]"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UnionType) and self.types_set == other.types_set

    def __repr__(self):
        args = ", ".join(repr(arg) for arg in self.types)
        return f"{self.__class__.__name__}({args})"


class ListType(Generic[T], BaseType[List[T]]):
    __slots__ = "type"

    def __init__(self, type_: BaseType[T]) -> None:
        self.type = type_

    def contains(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, ListType) and self.type.contains(other.type)

    def resolves(self, other: "BaseType[Any]") -> bool:
        return self.type.resolves(other)

    def accepts_resolved_object(self, obj: object) -> bool:
        return self.type.accepts_resolved_object(obj)

    def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
        return self.type.iterate_terminal_resolvable_types()

    def resolve_single_instance(self, resolver: IInstanceResolver) -> List[T]:
        return list(self.type.iterate_resolved_instances(resolver))

    def iterate_resolved_instances(
        self, resolver: IInstanceResolver
    ) -> Iterable[List[T]]:
        yield list(self.type.iterate_resolved_instances(resolver))

    def __hash__(self):
        return hash(("ListType", self.type))

    def __str__(self) -> str:
        return f"List[{self.type}]"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ListType) and other.type == self.type

    def __repr__(self):
        return f"{self.__class__.__name__}({self.type!r})"


class IterableType(Generic[T], BaseType[Iterable[T]]):
    __slots__ = "type"

    def __init__(self, type_: BaseType[T]) -> None:
        self.type = type_

    def contains(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, (IterableType, ListType)) and self.type.contains(
            other.type
        )

    def resolves(self, other: "BaseType[Any]") -> bool:
        return self.type.resolves(other)

    def accepts_resolved_object(self, obj: object) -> bool:
        return self.type.accepts_resolved_object(obj)

    def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
        return self.type.iterate_terminal_resolvable_types()

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

    def __repr__(self):
        return f"{self.__class__.__name__}({self.type!r})"


class TupleType(BaseType[Any]):
    __slots__ = "args"

    def __init__(self, *args: BaseType[Any]):
        self.args = args

    def contains(self, other: "BaseType[Any]") -> bool:
        return isinstance(other, TupleType) and all(
            a1.contains(a2) for (a1, a2) in zip(self.args, other.args)
        )

    def resolves(self, other: "BaseType[Any]") -> bool:
        return (
            isinstance(other, TupleType)
            and all(a1.resolves(a2) for (a1, a2) in zip(self.args, other.args))
        ) or any(arg.resolves(other) for arg in self.args)

    def accepts_resolved_object(self, obj: object) -> bool:
        if isinstance(obj, tuple) and len(obj) == len(self.args):
            for arg_type, arg_value in zip(self.args, obj):
                if not arg_type.accepts_resolved_object(arg_value):
                    return False
            return True
        return False

    def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
        yield self
        for arg in self.args:
            yield from arg.iterate_terminal_resolvable_types()

    def resolve_single_instance(self, resolver: IInstanceResolver) -> Iterable[Any]:
        try:
            return resolver.resolve_single_instance(self)
        except ResolutionError:
            return tuple(arg.resolve_single_instance(resolver) for arg in self.args)

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[Any]:
        yield from resolver.iterate_instances(self)

        for combination in product(
            *(arg.iterate_resolved_instances(resolver) for arg in self.args)
        ):
            yield combination

    def __str__(self) -> str:
        return f"Tuple[" + ",".join(str(arg) for arg in self.args) + "]"

    def __hash__(self) -> int:
        return hash(("TupleType", self.args))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TupleType) and self.args == other.args

    def __repr__(self):
        args = ", ".join(repr(arg) for arg in self.args)
        return f"{self.__class__.__name__}({args})"


class AnyType(BaseType[Any]):
    def accepts_resolved_object(self, obj: object) -> bool:
        return True

    def contains(self, other: "BaseType[Any]") -> bool:
        return True

    def resolves(self, other: "BaseType[Any]") -> bool:
        return True

    def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
        return (self,)

    def resolve_single_instance(self, resolver: IInstanceResolver) -> Iterable[Any]:
        return resolver.resolve_single_instance(self)

    def iterate_resolved_instances(self, resolver: IInstanceResolver) -> Iterable[Any]:
        return resolver.iterate_instances(self)

    def __str__(self) -> str:
        return "Any"

    def __hash__(self) -> int:
        return hash("AnyType")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AnyType)

    def __repr__(self):
        return f"{self.__class__.__name__}"


if sys.version_info >= (3, 8):
    from typing import Protocol

    _ProtocolType = type(Protocol)
    PROTOCOL_SUPPORTED = True

    class ProtocolType(BaseType[Any]):
        __slots__ = "_protocol"

        def __init__(self, protocol: type):
            if not getattr(protocol, "_is_runtime_protocol", False):
                raise TypeError(
                    f"Only runtime protocols are supported. "
                    f"Mark {protocol} with @runtime_checkable decorator."
                )
            self._protocol = protocol

        def contains(self, other: "BaseType[Any]") -> bool:
            if isinstance(other, ProtocolType):
                return issubclass(other._protocol, self._protocol)
            if isinstance(other, ClassType):
                return issubclass(other.type, self._protocol)
            return False

        def resolves(self, other: "BaseType[Any]") -> bool:
            if isinstance(other, ProtocolType):
                return issubclass(other._protocol, self._protocol)
            if isinstance(other, ClassType):
                return issubclass(other.type, self._protocol)
            return False

        def accepts_resolved_object(self, obj: object) -> bool:
            return isinstance(obj, self._protocol)

        def iterate_terminal_resolvable_types(self) -> Iterable["BaseType[Any]"]:
            return (self,)

        def resolve_single_instance(self, resolver: IInstanceResolver) -> Any:
            return resolver.resolve_single_instance(self)

        def iterate_resolved_instances(
            self, resolver: IInstanceResolver
        ) -> Iterable[Any]:
            return resolver.iterate_instances(self)

        def __str__(self) -> str:
            return str(self._protocol)

        def __hash__(self) -> int:
            return hash(("ProtocolType", self._protocol))

        def __eq__(self, other: object) -> bool:
            return isinstance(other, ProtocolType) and self._protocol == other._protocol

        def __repr__(self):
            return f"{self.__class__.__name__}({self._protocol!r})"

else:
    PROTOCOL_SUPPORTED = False


def intersects(t1: BaseType[Any], t2: BaseType[Any]) -> bool:
    for terminal1 in t1.iterate_terminal_resolvable_types():
        for terminal2 in t2.iterate_terminal_resolvable_types():
            if terminal1.resolves(terminal2) or terminal2.resolves(terminal1):
                return True
    return False


_NoneType = type(None)

ANY_TYPE = AnyType()
NONE_TYPE = NoneType()


@lru_cache(1024)
def as_type(type_: Type[T]) -> BaseType[T]:
    """Converts python types to custom type-system

    For collection base classes see:
    https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes

    :param type_: any python type
    :return: MetaType
    """
    type_ = unwrap_decorators(type_)

    if type_ is _NoneType:
        return NONE_TYPE  # type: ignore

    if type_ is Any:
        return ANY_TYPE

    if PROTOCOL_SUPPORTED:
        if type(type_) is _ProtocolType:  # type: ignore
            return ProtocolType(type_)

    if isinstance(type_, type):
        return ClassType[T](type_)

    # Generics
    origin = get_origin(type_)
    args = get_args(type_)

    if origin is not None and args:
        if origin is Union:
            return UnionType(*(as_type(t) for t in args))

        if origin is tuple:
            return TupleType(*(as_type(t) for t in args))

        if issubclass(origin, collections_abc.Sequence):
            return ListType(as_type(args[0]))

        if issubclass(origin, collections_abc.Iterable):
            return IterableType(as_type(args[0]))

        if origin is type:
            return TypeOfType(as_type(args[0]))

    raise TypeError(f"Unsupported type {type_}")


def type_of(obj: object) -> BaseType[Any]:
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

    if t is type:
        return TypeOfType(as_type(obj))

    if get_origin(obj) is not None:
        return TypeOfType(as_type(obj))

    return as_type(t)
