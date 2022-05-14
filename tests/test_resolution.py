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


# Constants to reduce test boilerplate
T_A = ClassType(A)
T_A_CHILD = ClassType(ChildOfA)
T_B = ClassType(B)
T_INT = ClassType(int)
T_STR = ClassType(str)


if sys.version_info >= (3, 8):

    @tp.runtime_checkable
    class AProtocol(tp.Protocol):
        def foo(self):
            pass

    PROTOCOL_TYPE_CONVERSION_CASES = [
        (AProtocol, ProtocolType(AProtocol)),
    ]

    PROTOCOL_TYPE_CONTAINS_SELF_CASES = [
        ProtocolType(AProtocol),
    ]

    PROTOCOL_TYPE_CONTAINS_CASES = [
        (ProtocolType(AProtocol), T_A_CHILD),
    ]

    PROTOCOL_TYPE_RESOLVES_CASES = [
        (ProtocolType(AProtocol), T_A),
        (ProtocolType(AProtocol), T_A_CHILD),
        (ProtocolType(AProtocol), ProtocolType(AProtocol)),
        (ListType(ProtocolType(AProtocol)), T_A_CHILD),
        (TypeOfType(ProtocolType(AProtocol)), TypeOfType(T_A)),
        (TypeOfType(ProtocolType(AProtocol)), TypeOfType(T_A_CHILD)),
    ]

    PROTOCOL_TYPE_NOT_RESOLVES_CASES = [
        (ProtocolType(AProtocol), T_B),
    ]

    PROTOCOL_TYPE_INTERSECT_SELF_CASES = [
        ProtocolType(AProtocol),
    ]

    PROTOCOL_TYPE_INTERSECTS_CASES = [
        (ProtocolType(AProtocol), T_A),
        (ProtocolType(AProtocol), T_A_CHILD),
    ]

    PROTOCOL_TYPE_ACCEPTS_OBJECT_CASES = [
        (ProtocolType(AProtocol), A()),
        (ProtocolType(AProtocol), ChildOfA()),
    ]

    PROTOCOL_TYPE_DOES_NOT_ACCEPT_OBJECT_CASES = [
        (ProtocolType(AProtocol), B()),
        (ProtocolType(AProtocol), "hello"),
        (ProtocolType(AProtocol), tp.List[A]),
    ]

else:
    # No Protocol -> no test cases
    PROTOCOL_TYPE_CONVERSION_CASES = []
    PROTOCOL_TYPE_CONTAINS_SELF_CASES = []
    PROTOCOL_TYPE_CONTAINS_CASES = []
    PROTOCOL_TYPE_RESOLVES_CASES = []
    PROTOCOL_TYPE_NOT_RESOLVES_CASES = []
    PROTOCOL_TYPE_INTERSECT_SELF_CASES = []
    PROTOCOL_TYPE_INTERSECTS_CASES = []
    PROTOCOL_TYPE_ACCEPTS_OBJECT_CASES = []
    PROTOCOL_TYPE_DOES_NOT_ACCEPT_OBJECT_CASES = []


@pytest.mark.parametrize(
    "py_type, meta_type",
    [
        (int, T_INT),
        (object, ClassType(object)),
        (A, T_A),
        (type(None), NONE_TYPE),
        (tp.Any, ANY_TYPE),
        (tp.Type[A], TypeOfType(T_A)),
        (tp.Type[tp.List[A]], TypeOfType(ListType(T_A))),
        (tp.List[int], ListType(T_INT)),
        (tp.List[A], ListType(T_A)),
        (tp.Iterable[int], IterableType(T_INT)),
        (tp.Iterable[A], IterableType(T_A)),
        (tp.Union[A], T_A),
        (tp.Union[A, None], UnionType(T_A, NONE_TYPE)),
        (tp.Optional[A], UnionType(T_A, NONE_TYPE)),
        (
            tp.Union[A, B, None],
            UnionType(T_A, T_B, NONE_TYPE),
        ),
        (tp.Tuple[A, B], TupleType(T_A, T_B)),
        (tp.Tuple[A], TupleType(T_A)),
        *PROTOCOL_TYPE_CONVERSION_CASES,
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
        tp.NoReturn,
    ],
)
def test_python_type_conversions_unsupported_types_raises(py_type: tp.Any):
    with pytest.raises(TypeError):
        as_type(py_type)


@pytest.mark.parametrize(
    "obj, expected_type",
    [
        ("a", T_STR),
        (42, T_INT),
        (None, NONE_TYPE),
        ([1, 2, 3], ListType(T_INT)),
        ([], ClassType(list)),
        (tuple(), ClassType(tuple)),
        ([1, "string", 3], ListType(UnionType(T_INT, T_STR))),
        ((1, 2, 3), TupleType(T_INT, T_INT, T_INT)),
        ((1, "string", 3), TupleType(T_INT, T_STR, T_INT)),
        # Higher order
        (int, TypeOfType(T_INT)),
        (str, TypeOfType(T_STR)),
        (tp.List[str], TypeOfType(ListType(T_STR))),
        # Even higher order
        (tp.Type[str], TypeOfType(TypeOfType(T_STR))),
        (tp.Type[tp.List[str]], TypeOfType(TypeOfType(ListType(T_STR)))),
    ],
)
def test_type_of(obj, expected_type):
    assert type_of(obj) == expected_type


@pytest.mark.parametrize(
    "a",
    [
        ANY_TYPE,
        NONE_TYPE,
        T_A,
        # UnionType(TYPE_A, NONE_TYPE), # Not sure how this should work atm
        ListType(T_A),
        IterableType(T_A),
        TypeOfType(T_A),
        TupleType(T_A, T_B),
        *PROTOCOL_TYPE_CONTAINS_SELF_CASES,
    ],
)
def test_type_contains_self(a: BaseType[tp.Any]):
    assert a.contains(a)


@pytest.mark.parametrize(
    "a, b",
    [
        (ANY_TYPE, NONE_TYPE),
        (ANY_TYPE, T_A),
        (T_A, T_A_CHILD),
        (UnionType(T_A, NONE_TYPE), T_A),
        (UnionType(T_A, NONE_TYPE), T_A_CHILD),
        (UnionType(T_A, NONE_TYPE), NONE_TYPE),
        (ListType(T_A), ListType(T_A_CHILD)),
        (IterableType(T_A), IterableType(T_A_CHILD)),
        (IterableType(T_A), ListType(T_A)),
        (IterableType(T_A), ListType(T_A_CHILD)),
        (TypeOfType(T_A), TypeOfType(T_A_CHILD)),
        (TupleType(T_A, T_B), TupleType(T_A_CHILD, T_B)),
        *PROTOCOL_TYPE_CONTAINS_CASES,
    ],
)
def test_type_contains_type(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert a.contains(b)


@pytest.mark.parametrize(
    "a, b",
    [
        (ANY_TYPE, NONE_TYPE),
        (ANY_TYPE, ANY_TYPE),
        (NONE_TYPE, NONE_TYPE),
        (ANY_TYPE, T_A),
        (TypeOfType(T_A), TypeOfType(T_A)),
        (TypeOfType(T_A), TypeOfType(T_A_CHILD)),
        (
            TypeOfType(UnionType(T_A, T_B)),
            TypeOfType(T_A_CHILD),
        ),
        (T_A, T_A_CHILD),
        (ListType(T_A), T_A),
        (ListType(T_A), T_A_CHILD),
        (IterableType(T_A), T_A),
        (IterableType(T_A), T_A_CHILD),
        (UnionType(T_A, NONE_TYPE), T_A),
        (UnionType(T_A, NONE_TYPE), T_A_CHILD),
        (UnionType(T_A, NONE_TYPE), NONE_TYPE),
        (TupleType(T_A, T_B), T_A),
        (TupleType(T_A, T_B), T_A_CHILD),
        (TupleType(T_A, T_B), TupleType(T_A, T_B)),
        (
            TupleType(T_A, T_B),
            TupleType(T_A_CHILD, T_B),
        ),
        *PROTOCOL_TYPE_RESOLVES_CASES,
    ],
)
def test_type_resolves_type(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert a.resolves(b)


@pytest.mark.parametrize(
    "a, b",
    [
        (NONE_TYPE, ANY_TYPE),
        (T_A, T_B),
        (T_A, ANY_TYPE),
        (T_A, NONE_TYPE),
        (T_A_CHILD, T_A),
        (UnionType(T_A, NONE_TYPE), T_B),
        (UnionType(T_A_CHILD, NONE_TYPE), T_A),
        (TupleType(T_A_CHILD, T_B), T_A),
        (
            TupleType(T_A_CHILD, T_B),
            TupleType(T_A, T_B),
        ),
        *PROTOCOL_TYPE_NOT_RESOLVES_CASES,
    ],
)
def test_type_not_resolves_type(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert not a.resolves(b)


@pytest.mark.parametrize(
    "t",
    [
        NONE_TYPE,
        ANY_TYPE,
        T_A,
        T_A_CHILD,
        TypeOfType(T_A),
        *PROTOCOL_TYPE_INTERSECT_SELF_CASES,
    ],
)
def test_terminal_type_intersects_self(t: BaseType[tp.Any]):
    assert intersects(t, t)


@pytest.mark.parametrize(
    "a, b",
    [
        (T_A, T_A_CHILD),
        (TypeOfType(T_A), TypeOfType(T_A)),
        (TypeOfType(T_A), TypeOfType(T_A_CHILD)),
        (
            TypeOfType(UnionType(T_A, T_B)),
            TypeOfType(T_A_CHILD),
        ),
        (UnionType(T_A, NONE_TYPE), NONE_TYPE),
        (UnionType(T_A, NONE_TYPE), T_A),
        (UnionType(T_A, NONE_TYPE), T_A_CHILD),
        (UnionType(T_A, NONE_TYPE), UnionType(NONE_TYPE, T_A)),
        (UnionType(T_A, NONE_TYPE), UnionType(T_B, T_A)),
        (
            UnionType(T_A, NONE_TYPE),
            UnionType(T_B, T_A_CHILD),
        ),
        (ListType(T_A), T_A_CHILD),
        (ListType(T_A), T_A),
        (IterableType(T_A), T_A_CHILD),
        (IterableType(T_A), T_A),
        (TupleType(T_A, T_B), T_A),
        (TupleType(T_A, T_B), T_B),
        (TupleType(T_A, T_B), T_A_CHILD),
        (TupleType(T_A, T_B), TupleType(T_A, T_B)),
        (TupleType(T_A, T_B), TupleType(T_B, T_A)),
        (
            TupleType(T_A, T_B),
            TupleType(T_A_CHILD, T_B),
        ),
        (
            TupleType(T_A, T_B),
            TupleType(T_B, T_A_CHILD),
        ),
        *PROTOCOL_TYPE_INTERSECTS_CASES,
    ],
)
def test_type_intersects_type(a: BaseType[tp.Any], b: BaseType[tp.Any]):
    assert intersects(a, b)
    assert intersects(b, a)


@pytest.mark.parametrize(
    "t, obj",
    [
        (ANY_TYPE, A()),
        (ANY_TYPE, B()),
        (ANY_TYPE, None),
        (NONE_TYPE, None),
        (T_INT, 42),
        (T_A, A()),
        (T_A, ChildOfA()),
        (UnionType(T_A, T_B), A()),
        (UnionType(T_A, T_B), ChildOfA()),
        (UnionType(T_A, T_B), B()),
        (UnionType(T_A, NONE_TYPE), ChildOfA()),
        (ListType(T_A), A()),
        (IterableType(T_A), A()),
        (TypeOfType(T_A), A),
        (TypeOfType(ListType(T_A)), tp.List[A]),
        (TypeOfType(ListType(T_A)), tp.List[ChildOfA]),
        *PROTOCOL_TYPE_ACCEPTS_OBJECT_CASES,
    ],
)
def test_type_accepts_resolved_object(t: BaseType[tp.Any], obj):
    assert t.accepts_resolved_object(obj)


@pytest.mark.parametrize(
    "t, obj",
    [
        (NONE_TYPE, A()),
        (NONE_TYPE, B()),
        (T_INT, "hello"),
        (T_A, B()),
        (T_A, "hello"),
        (T_A_CHILD, A()),
        (UnionType(T_A_CHILD, T_B), A()),
        (UnionType(T_A_CHILD, T_B), NONE_TYPE),
        (ListType(T_A_CHILD), A()),
        (ListType(T_A), B()),
        (IterableType(T_A), B()),
        (IterableType(T_A_CHILD), B()),
        (TypeOfType(T_A_CHILD), A),
        (TypeOfType(T_A), B),
        (TypeOfType(T_A), 42),
        (TypeOfType(T_A), "hello"),
        (TypeOfType(T_A), None),
        (TypeOfType(ListType(T_A_CHILD)), tp.List[A]),
        (TypeOfType(ListType(T_A)), tp.List[B]),
        *PROTOCOL_TYPE_DOES_NOT_ACCEPT_OBJECT_CASES,
    ],
)
def test_type_does_not_accept_object(t: BaseType[tp.Any], obj):
    assert not t.accepts_resolved_object(obj)
