import collections
import contextlib
import typing
import pytest
import sys
from collections import abc as abc_collections


from typedi.typing_utils import (
    eval_type,
    ForwardRef,
    get_origin,
)

TEST_TYPES = [
    int,
    str,
    float,
    bool,
    type(None),
    typing.Any,
    typing.List,
    typing.Tuple,
    typing.List[int],
    typing.Optional[int],
    typing.Union[int, str],
]


@pytest.mark.parametrize("tp", TEST_TYPES)
def test_eval_type_resolves_non_forward_ref_types(tp):
    assert eval_type(tp, globals(), locals()) == tp


def test_eval_type_resolves_forward_ref():
    class MyClass:
        pass

    assert eval_type(ForwardRef("MyClass"), globals(), locals()) == MyClass


def test_nested_eval_type_resolves_forward_ref():
    class MyClass:
        pass

    assert (
        eval_type(typing.Optional[ForwardRef("MyClass")], globals(), locals())
        == typing.Optional[MyClass]
    )


T = typing.TypeVar("T")


class CustomGeneric(typing.Generic[T]):
    pass


TYPE_ORIGINS = [
    (int, None),
    (object, None),
    (list, None),
    (bytes, None),
    (type, None),
    (typing.Any, None),
    (ForwardRef("A"), None),
    # (typing.Annotated[int, 42], int), # py3.9+
    (typing.Union[int, None], typing.Union),
    (typing.Generic[T], typing.Generic),
    (typing.Generic, typing.Generic),
    (CustomGeneric[int], CustomGeneric),
    # collections.abc
    (typing.Awaitable[int], abc_collections.Awaitable),
    (typing.Coroutine[int, int, int], abc_collections.Coroutine),
    (typing.AsyncIterable[int], abc_collections.AsyncIterable),
    (typing.AsyncIterator[int], abc_collections.AsyncIterator),
    (typing.Iterable[int], abc_collections.Iterable),
    (typing.Iterator[int], abc_collections.Iterator),
    (typing.Reversible[int], abc_collections.Reversible),
    (typing.Container[int], abc_collections.Container),
    (typing.Collection[int], abc_collections.Collection),
    (typing.Callable[[int], int], abc_collections.Callable),
    (typing.AbstractSet[int], abc_collections.Set),
    (typing.MutableSet[int], abc_collections.MutableSet),
    (typing.Mapping[str, str], abc_collections.Mapping),
    (typing.MutableMapping[str, str], abc_collections.MutableMapping),
    (typing.Sequence[str], abc_collections.Sequence),
    (typing.MutableSequence[str], abc_collections.MutableSequence),
    (typing.MappingView[str], abc_collections.MappingView),
    (typing.KeysView[str], abc_collections.KeysView),
    (typing.ItemsView[str, str], abc_collections.ItemsView),
    (typing.ValuesView[str], abc_collections.ValuesView),
    (typing.Generator[int, int, int], abc_collections.Generator),
    (typing.AsyncGenerator[int, int], abc_collections.AsyncGenerator),
    # contextlib
    (typing.ContextManager[str], contextlib.AbstractContextManager),
    (typing.AsyncContextManager[str], contextlib.AbstractAsyncContextManager),
    # Builtin collections
    (typing.List[int], list),
    (typing.Set[int], set),
    (typing.FrozenSet[int], frozenset),
    (typing.Dict[str, int], dict),
    (typing.Tuple[str, int], tuple),
    (typing.Tuple[str, ...], tuple),
    (typing.Type[int], type),
    # collections
    (typing.Deque[int], collections.deque),
    (typing.DefaultDict[int, int], collections.defaultdict),
    (typing.OrderedDict[int, int], collections.OrderedDict),
    (typing.Counter[int], collections.Counter),
    (typing.ChainMap[int, int], collections.ChainMap),
]

if sys.version_info >= (3, 8):
    TYPE_ORIGINS.append((typing.Final[int], typing.Final))


@pytest.mark.parametrize("tp, expected", TYPE_ORIGINS)
def test_get_origin(tp, expected):
    assert get_origin(tp) is expected
