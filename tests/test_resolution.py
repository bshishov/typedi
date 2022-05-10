import sys
import typing as tp

import pytest

from typedi.resolution import *


class A:
    def foo(self):
        pass


class B:
    pass


class ChildOfA(A):
    pass


TYPE_CONVERSION_CASES = [
    (int, ClassType(int)),
    (object, ClassType(object)),
    (A, ClassType(A)),
    (type(None), NONE_TYPE),
    (tp.Any, ANY_TYPE),
    (tp.Type[A], TypeOfType(ClassType(A))),
    (tp.List[int], ListType(ClassType(int))),
    (tp.List[A], ListType(ClassType(A))),
    (tp.Iterable[int], IterableType(ClassType(int))),
    (tp.Iterable[A], IterableType(ClassType(A))),
    (tp.Union[A], ClassType(A)),
    (tp.Union[A, None], UnionType(ClassType(A), NONE_TYPE)),
    (tp.Optional[A], UnionType(ClassType(A), NONE_TYPE)),
    (
        tp.Union[A, B, None],
        UnionType(ClassType(A), ClassType(B), NONE_TYPE),
    ),
    (tp.Tuple[A, B], TupleType(ClassType(A), ClassType(B))),
    (tp.Tuple[A], TupleType(ClassType(A))),
]


TYPE_CONTAINS_CASES = [
    (ANY_TYPE, NONE_TYPE),
    (ANY_TYPE, ANY_TYPE),
    (NONE_TYPE, NONE_TYPE),
    (ANY_TYPE, ClassType(A)),
    (TypeOfType(ClassType(A)), TypeOfType(ClassType(A))),
    (TypeOfType(ClassType(A)), TypeOfType(ClassType(ChildOfA))),
    (TypeOfType(UnionType(ClassType(A), ClassType(B))), TypeOfType(ClassType(ChildOfA))),
    (ClassType(A), ClassType(ChildOfA)),
    (ListType(ClassType(A)), ClassType(A)),
    (ListType(ClassType(A)), ClassType(ChildOfA)),
    (IterableType(ClassType(A)), ClassType(A)),
    (IterableType(ClassType(A)), ClassType(ChildOfA)),
    (UnionType(ClassType(A), NONE_TYPE), ClassType(A)),
    (UnionType(ClassType(A), NONE_TYPE), ClassType(ChildOfA)),
    (UnionType(ClassType(A), NONE_TYPE), NONE_TYPE),
    (TupleType(ClassType(A), ClassType(B)), ClassType(A)),
    (TupleType(ClassType(A), ClassType(B)), ClassType(ChildOfA)),
    (TupleType(ClassType(A), ClassType(B)), TupleType(ClassType(A), ClassType(B))),
    (
        TupleType(ClassType(A), ClassType(B)),
        TupleType(ClassType(ChildOfA), ClassType(B)),
    ),
]

TYPE_NOT_CONTAINS_CASES = [
    (NONE_TYPE, ANY_TYPE),
    (ClassType(A), ClassType(B)),
    (ClassType(A), ANY_TYPE),
    (ClassType(A), NONE_TYPE),
    (ClassType(ChildOfA), ClassType(A)),
    (UnionType(ClassType(A), NONE_TYPE), ClassType(B)),
    (UnionType(ClassType(ChildOfA), NONE_TYPE), ClassType(A)),
    (TupleType(ClassType(ChildOfA), ClassType(B)), ClassType(A)),
    (
        TupleType(ClassType(ChildOfA), ClassType(B)),
        TupleType(ClassType(A), ClassType(B)),
    ),
]


INTERSECT_SELF_CASES = [
    NONE_TYPE,
    ANY_TYPE,
    ClassType(A),
    ClassType(ChildOfA),
    TypeOfType(ClassType(A)),
]


INTERSECTS_CASES = [
    (ClassType(A), ClassType(ChildOfA)),
    (TypeOfType(ClassType(A)), TypeOfType(ClassType(A))),
    (TypeOfType(ClassType(A)), TypeOfType(ClassType(ChildOfA))),
    (TypeOfType(UnionType(ClassType(A), ClassType(B))), TypeOfType(ClassType(ChildOfA))),
    (UnionType(ClassType(A), NONE_TYPE), NONE_TYPE),
    (UnionType(ClassType(A), NONE_TYPE), ClassType(A)),
    (UnionType(ClassType(A), NONE_TYPE), ClassType(ChildOfA)),
    (UnionType(ClassType(A), NONE_TYPE), UnionType(NONE_TYPE, ClassType(A))),
    (UnionType(ClassType(A), NONE_TYPE), UnionType(ClassType(B), ClassType(A))),
    (
        UnionType(ClassType(A), NONE_TYPE),
        UnionType(ClassType(B), ClassType(ChildOfA)),
    ),
    (ListType(ClassType(A)), ClassType(ChildOfA)),
    (ListType(ClassType(A)), ClassType(A)),
    (IterableType(ClassType(A)), ClassType(ChildOfA)),
    (IterableType(ClassType(A)), ClassType(A)),
    (TupleType(ClassType(A), ClassType(B)), ClassType(A)),
    (TupleType(ClassType(A), ClassType(B)), ClassType(B)),
    (TupleType(ClassType(A), ClassType(B)), ClassType(ChildOfA)),
    (TupleType(ClassType(A), ClassType(B)), TupleType(ClassType(A), ClassType(B))),
    (TupleType(ClassType(A), ClassType(B)), TupleType(ClassType(B), ClassType(A))),
    (
        TupleType(ClassType(A), ClassType(B)),
        TupleType(ClassType(ChildOfA), ClassType(B)),
    ),
    (
        TupleType(ClassType(A), ClassType(B)),
        TupleType(ClassType(B), ClassType(ChildOfA)),
    ),
]

TYPE_ACCEPTS_RESOLVED_OBJECT_TEST_CASES = [
    (ANY_TYPE, A()),
    (ANY_TYPE, B()),
    (ANY_TYPE, None),
    (NONE_TYPE, None),
    (ClassType(int), 42),
    (ClassType(A), A()),
    (ClassType(A), ChildOfA()),
    (UnionType(ClassType(A), ClassType(B)), A()),
    (UnionType(ClassType(A), ClassType(B)), ChildOfA()),
    (UnionType(ClassType(A), ClassType(B)), B()),
    (UnionType(ClassType(A), NONE_TYPE), ChildOfA()),
    (ListType(ClassType(A)), A()),
    (IterableType(ClassType(A)), A()),
    (TypeOfType(ClassType(A)), A),
    (TypeOfType(ListType(ClassType(A))), tp.List[A]),
    (TypeOfType(ListType(ClassType(A))), tp.List[ChildOfA]),
]


if sys.version_info >= (3, 8):

    @tp.runtime_checkable
    class AProtocol(tp.Protocol):
        def foo(self):
            pass

    TYPE_CONVERSION_CASES.extend(
        [
            (AProtocol, ProtocolType(AProtocol)),
        ]
    )

    TYPE_CONTAINS_CASES.extend(
        [
            (ProtocolType(AProtocol), ClassType(A)),
            (ProtocolType(AProtocol), ClassType(ChildOfA)),
            (ProtocolType(AProtocol), ProtocolType(AProtocol)),
            (ListType(ProtocolType(AProtocol)), ClassType(ChildOfA)),
            (TypeOfType(ProtocolType(AProtocol)), TypeOfType(ClassType(A))),
            (TypeOfType(ProtocolType(AProtocol)), TypeOfType(ClassType(ChildOfA))),
        ]
    )

    TYPE_NOT_CONTAINS_CASES.extend(
        [
            (ProtocolType(AProtocol), ClassType(B)),
        ]
    )

    INTERSECT_SELF_CASES.extend(
        [
            ProtocolType(AProtocol),
        ]
    )

    INTERSECTS_CASES.extend(
        [
            (ProtocolType(AProtocol), ClassType(A)),
            (ProtocolType(AProtocol), ClassType(ChildOfA)),
        ]
    )


@pytest.mark.parametrize("py_type, meta_type", TYPE_CONVERSION_CASES)
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
        tp.NoReturn,
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
        (None, NONE_TYPE),
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


@pytest.mark.parametrize("a, b", TYPE_CONTAINS_CASES)
def test_contains(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert a.contains(b)


@pytest.mark.parametrize("a, b", TYPE_NOT_CONTAINS_CASES)
def test_not_contains(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert not a.contains(b)


@pytest.mark.parametrize("t", INTERSECT_SELF_CASES)
def test_terminals_intersects_self(t: BaseType[tp.Any]):
    assert intersects(t, t)


@pytest.mark.parametrize("a, b", INTERSECTS_CASES)
def test_intersects(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert intersects(a, b)
    assert intersects(b, a)


@pytest.mark.parametrize("t, obj", TYPE_ACCEPTS_RESOLVED_OBJECT_TEST_CASES)
def test_type_accepts_object(t: BaseType[tp.Any], obj):
    assert t.accepts_resolved_object(obj)
