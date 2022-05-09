import sys
import typing
from typing import (
    Any,
    Type,
    Callable,
    Union,
    TypeVar,
    Mapping,
    Tuple,
    Generic,
    get_type_hints,
)
from functools import partial, partialmethod

__all__ = [
    "eval_type",
    "unwrap_decorators",
    "get_return_type",
    "type_forward_ref_scope",
    "get_origin",
    "get_args",
]


T = TypeVar("T")


# Evaluates meta types recursively including ForwardRef
# 3.6  : https://github.com/python/cpython/blob/3.6/Lib/typing.py#L348
# 3.7  : https://github.com/python/cpython/blob/3.7/Lib/typing.py#L258
# 3.8  : https://github.com/python/cpython/blob/3.8/Lib/typing.py#L265
# 3.9  : https://github.com/python/cpython/blob/3.9/Lib/typing.py#L285
# 3.10 : https://github.com/python/cpython/blob/3.10/Lib/typing.py#L319
eval_type = getattr(typing, "_eval_type")


def unwrap_decorators(o: Any) -> Any:
    """Unwraps decorators to get actual decorated class or function"""
    while hasattr(o, "__wrapped__"):
        o = o.__wrapped__
    return o


def get_return_type(obj: Union[Type[T], Callable[..., T]]) -> Union[Type[T], type]:
    """Returns the actual type, being produced by type or callable.

    It handles decorators, partials, ForwardRefs and their combinations.
    """
    obj = unwrap_decorators(obj)

    if isinstance(obj, type):
        # Classes produce themselves
        return obj

    # Partial is an object of class "functools.partial"
    # So we need to resolve return type from the wrapped function
    if isinstance(obj, (partial, partialmethod)):
        return get_return_type(obj.func)

    try:
        # Functions and methods
        callable_type_hints = get_type_hints(obj)
    except TypeError:
        # obj is not a function or method, but a valid callable object
        callable_type_hints = get_type_hints(obj.__call__)  # type: ignore

    if "return" not in callable_type_hints:
        raise TypeError(f"Missing return type annotation for {obj}")

    r_type: Union[Type[T], type] = callable_type_hints["return"]
    return r_type


def type_forward_ref_scope(
    type_: Union[Type[T], Callable[..., T]]
) -> Mapping[str, Any]:
    """Returns dict scope for ForwardRef evaluation for use in _eval_type
    Right now only module-level ForwardRefs are supported.

    Note: this function does not unwrap decorators (it is done outside)
    TODO: make it work for base-classes defined in separate modules (MRO hierarchy)

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


def get_origin(type_: Any) -> Any:
    """Get unsubscribed version of `type_`.
    Examples:
        get_origin(int) is None
        get_origin(typing.Any) is None
        get_origin(typing.List[int]) is list
        get_origin(typing.Literal[123]) is typing.Literal
        get_origin(typing.Generic[T]) is typing.Generic
        get_origin(typing.Generic) is typing.Generic
        get_origin(typing.Annotated[int, "some"]) is int

    NOTE: This method intentionally allows Annotated to proxy __origin__
    """
    if type_ is Generic:  # Special case
        return type_
    return getattr(type_, "__origin__", None)


def get_args(type_: Any) -> Tuple[Any, ...]:
    """Get type arguments with all substitutions performed.
    For unions, basic simplifications used by Union constructor are performed.

    Examples:
        get_args(Dict[str, int]) == (str, int)
        get_args(int) == ()
        get_args(Union[int, Union[T, int], str][int]) == (int, str)
        get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
        get_args(Callable[[], T][int]) == ([], int)
    """
    return getattr(type_, "__args__", tuple())
