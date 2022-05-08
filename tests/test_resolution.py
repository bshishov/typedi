import pytest
import typing as tp

from typedi.resolution import *


class A:
    pass


class B:
    pass


@tp.runtime_checkable
class AProtocol(tp.Protocol):
    pass


@pytest.mark.parametrize(
    "py_type, meta_type",
    [
        (int, ClassType(int)),
        (object, ClassType(object)),
        (A, ClassType(A)),
        (type(None), NoneTerminalType()),
        (tp.Any, AnyType()),
        (AProtocol, ProtocolType(AProtocol)),
        (tp.Type[A], GenericTerminalType(tp.Type[A])),
        (tp.List[int], ListType(ClassType(int))),
        (tp.List[A], ListType(ClassType(A))),
        (tp.Iterable[int], IterableType(ClassType(int))),
        (tp.Iterable[A], IterableType(ClassType(A))),
        (tp.Union[A], ClassType(A)),
        (tp.Union[A, None], UnionType(ClassType(A), NoneTerminalType())),
        (tp.Optional[A], UnionType(ClassType(A), NoneTerminalType())),
        (
            tp.Union[A, B, None],
            UnionType(ClassType(A), ClassType(B), NoneTerminalType()),
        ),
        (tp.Tuple[A, B], TupleType(ClassType(A), ClassType(B))),
        (tp.Tuple[A], TupleType(ClassType(A))),
    ],
)
def test_python_type_valid_conversion(py_type: tp.Any, meta_type: BaseType[tp.Any]):
    assert as_type(py_type) == meta_type


T = tp.TypeVar("T")


@pytest.mark.parametrize(
    "py_type",
    [
        ...,
        T,
        object(),
        tp.Union,
        tp.List,
        tp.Iterable,
        tp.Tuple[A, ...],
        tp.Union[T],
        tp.List[T],
        tp.Iterable[T],
        tp.Tuple[T, A],
        tp.Tuple[A, T],
        tp.Tuple[T, ...],
    ],
)
def test_python_type_conversions_unsupported_types_raises(py_type: tp.Any):
    with pytest.raises(TypeError):
        as_type(py_type)


@pytest.mark.parametrize(
    "obj, expected_type",
    [
        ("a", ClassType(str)),
        (42, ClassType(int)),
        (None, NoneTerminalType()),
        ([1, 2, 3], ListType(ClassType(int))),
        ([], ClassType(list)),
        (tuple(), ClassType(tuple)),
        ([1, "string", 3], ListType(UnionType(ClassType(int), ClassType(str)))),
        ((1, 2, 3), TupleType(ClassType(int), ClassType(int), ClassType(int))),
        ((1, "string", 3), TupleType(ClassType(int), ClassType(str), ClassType(int))),
    ],
)
def test_type_of(obj, expected_type):
    assert type_of(obj) == expected_type
