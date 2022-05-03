import pytest
import typing as tp

from typedi.resolution import *


class A:
    pass


class B:
    pass


@pytest.mark.parametrize(
    "py_type, meta_type",
    [
        (int, ClassType(int)),
        (object, ClassType(object)),
        (A, ClassType(A)),
        (type(None), NoneTerminalType()),
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
def test_python_type_valid_conversion(py_type: tp.Any, meta_type: MetaType[tp.Any]):
    assert python_type_to_meta(py_type) == meta_type


T = tp.TypeVar("T")


@pytest.mark.parametrize(
    "py_type",
    [
        ...,
        T,
        object(),
        tp.Any,
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
        python_type_to_meta(py_type)
