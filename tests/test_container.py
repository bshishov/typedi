from typing import Optional, Union, List, Iterable, Type, Tuple, Any
import pytest
from functools import partial, wraps, partialmethod

from typedi import Container, ResolutionError


@pytest.fixture
def container() -> Container:
    return Container()


def test_register_instance(container: Container):
    class A:
        pass

    instance = A()
    container.register_instance(instance)
    assert container.resolve(A) is instance


def test_resolve_missing_instance_raises(container: Container):
    class A:
        pass

    with pytest.raises(ResolutionError):
        container.resolve(A)


def test_resolve_class_produces_different_instances(container: Container):
    class A:
        pass

    container.register_class(A)

    instance1 = container.resolve(A)
    instance2 = container.resolve(A)
    assert isinstance(instance1, A)
    assert isinstance(instance2, A)
    assert instance1 is not instance2


def test_register_factory(container: Container):
    class A:
        pass

    instance = A()

    def factory() -> A:
        return instance

    container.register_factory(factory)

    assert container.resolve(A) is instance


def test_register_factory_without_return_type_raises(container: Container):
    def factory():
        pass

    with pytest.raises(TypeError):
        container.register_factory(factory)


def test_register_partial(container: Container):
    class A:
        def __init__(self, param):
            self.param = param

    container.register_factory(partial(A, param=1))

    instance = container.resolve(A)
    assert isinstance(instance, A)
    assert instance.param == 1


def test_register_partial_method(container: Container):
    class B:
        def __init__(self, param):
            self.param = param

    class A:
        @classmethod
        def _create_b(cls, param) -> B:
            return B(param)

        create_b = partialmethod(_create_b, 1)

    container.register_factory(A.create_b)  # type: ignore

    instance = container.resolve(B)
    assert isinstance(instance, B)
    assert instance.param == 1


def test_register_partial_factory(container: Container):
    class A:
        def __init__(self, param):
            self.param = param

    def factory(param: int) -> A:
        return A(param)

    container.register_factory(partial(factory, param=1))

    instance = container.resolve(A)
    assert isinstance(instance, A)
    assert instance.param == 1


def test_singleton_factory(container: Container):
    class A:
        pass

    def factory_that_called_once() -> A:
        return A()

    container.register_singleton_factory(factory_that_called_once)

    instance1 = container.resolve(A)
    instance2 = container.resolve(A)
    assert instance1 is instance2


def decorator(f):
    @wraps(f)
    def _inner(*args, **kwargs):
        return f(*args, **kwargs)

    return _inner


def test_register_decorated_factory(container: Container):
    class B:
        pass

    class A:
        pass

    @decorator
    def factory(b: B) -> A:
        return A()

    container.register_class(B)
    container.register_factory(factory)
    assert isinstance(container.resolve(A), A)


def test_decorated_class(container: Container):
    @decorator
    class A:
        pass

    container.register_class(A)
    assert container.resolve(A)


def test_singleton_class(container: Container):
    class A:
        pass

    container.register_singleton_class(A)

    instance1 = container.resolve(A)
    instance2 = container.resolve(A)
    assert instance1 is instance2


def test_factory_of_generic(container: Container):
    class A:
        pass

    def factory() -> Type[A]:
        return A

    container.register_factory(factory)
    assert container.resolve(Type[A]) == A


def test_factory_of_weird_type(container: Container):
    class A:
        pass

    instance = A()

    def factory() -> List[Optional[A]]:
        return [instance, None]

    container.register_factory(factory)
    assert container.resolve(List[Optional[A]]) == [instance, None]

    # TODO: make it possible?
    # assert container.resolve(List[A]]) == [instance]


def test_inheritance_resolution(container: Container):
    class A:
        pass

    class ChildOfA(A):
        pass

    container.register_class(ChildOfA)
    assert isinstance(container.resolve(A), ChildOfA)


def test_register_missing_annotation_raises(container: Container):
    class A:
        def __init__(self, foo):
            self.foo = foo

    with pytest.raises(TypeError):
        container.register_class(A)


def test_register_missing_annotation_with_default_not_raises(container: Container):
    class A:
        def __init__(self, foo="bar"):
            self.foo = foo

    container.register_class(A)
    assert isinstance(container.resolve(A), A)


def test_invalid_annotations_with_default_still_resolves(container: Container):
    class A:
        def __init__(self, param: 123):
            self.param = param

    container.register_factory(partial(A, "wtf?"))
    container.resolve(A)


def test_callable_class_as_factory(container: Container):
    class A:
        pass

    class Factory:
        def __call__(self) -> A:
            return A()

    container.register_factory(Factory())
    assert isinstance(container.resolve(A), A)


def test_kwargs_are_ignored(container: Container):
    class A:
        pass

    def factory(**kwargs) -> A:
        return A()

    container.register_factory(factory)
    assert isinstance(container.resolve(A), A)


def test_positional_arguments_require_annotation(container: Container):
    class A:
        pass

    def factory(*args) -> A:
        return A()

    with pytest.raises(TypeError):
        container.register_factory(factory)


# region: Dependencies


def test_resolution_provides_a_container(container: Container):
    class A:
        pass

    def factory(c: Container) -> A:
        assert c is container
        return A()

    container.register_factory(factory)
    assert isinstance(container.resolve(A), A)


def test_resolve_class_dependencies(container: Container):
    class B:
        pass

    class A:
        def __init__(self, b: B):
            self.b = b

    b_instance = B()
    container.register_instance(b_instance)
    container.register_class(A)
    a_instance = container.resolve(A)

    assert a_instance.b is b_instance


def test_resolve_factory_dependencies(container: Container):
    class B:
        pass

    class A:
        def __init__(self, b: B):
            self.b = b

    def factory(b: B) -> A:
        return A(b)

    b_instance = B()
    container.register_instance(b_instance)
    container.register_factory(factory)
    a_instance = container.resolve(A)

    assert a_instance.b is b_instance


def test_missing_dependencies_raises_error(container: Container):
    class A:
        pass

    class B:
        pass

    class C:
        def __init__(self, a: A, b: B):
            self.a = a
            self.b = b

    container.register_class(B)
    container.register_class(C)

    with pytest.raises(ResolutionError):
        container.resolve(C)


class ForwardRefUser:
    def __init__(self, param: "ForwardReferredClass"):
        self.param = param


class ForwardRefUserList:
    def __init__(self, params: List["ForwardReferredClass"]):
        self.params = params


def forward_ref_factory() -> "ForwardReferredClass":
    return ForwardReferredClass()


def forward_ref_factory_of_generic() -> Type["ForwardReferredClass"]:
    return ForwardReferredClass


class ForwardReferredClass:
    pass


def test_forward_ref_dependencies(container: Container):
    # ForwardRef evaluation works only
    # for module-level declarations in the same user as the user class
    param_instance = ForwardReferredClass()
    container.register_instance(param_instance)
    container.register_class(ForwardRefUser)
    assert container.resolve(ForwardRefUser).param is param_instance


def test_forward_ref_list_dependencies(container: Container):
    # ForwardRef evaluation works only
    # for module-level declarations in the same user as the user class
    param_instance = ForwardReferredClass()
    container.register_instance(param_instance)
    container.register_class(ForwardRefUserList)
    assert container.resolve(ForwardRefUserList).params == [param_instance]


def test_forward_ref_factory(container: Container):
    # ForwardRef evaluation works only
    # for module-level declarations in the same user as the user class
    container.register_factory(forward_ref_factory)
    assert isinstance(container.resolve(ForwardReferredClass), ForwardReferredClass)


def test_forward_ref_factory_of_generic(container: Container):
    # ForwardRef evaluation works only
    # for module-level declarations in the same user as the user class
    container.register_factory(forward_ref_factory_of_generic)
    assert container.resolve(Type[ForwardReferredClass]) is ForwardReferredClass


# endregion: Dependencies

# region: Union


def test_union_types_resolution_first_available(container: Container):
    class A:
        pass

    class B:
        pass

    container.register_class(A)
    assert isinstance(container.resolve(Union[A, B]), A)


def test_union_types_resolution_when_one_provided(container: Container):
    class A:
        pass

    class B:
        pass

    container.register_class(B)
    assert isinstance(container.resolve(Union[A, B]), B)


def test_union_types_resolution_raises_when_none_provided(container: Container):
    class A:
        pass

    class B:
        pass

    with pytest.raises(ResolutionError):
        container.resolve(Union[A, B])


def test_union_types_resolution_with_none(container: Container):
    class A:
        pass

    class B:
        pass

    assert container.resolve(Union[A, B, None]) is None


def test_factory_returns_union(container: Container):
    class A:
        pass

    class B:
        pass

    def factory() -> Union[A, B]:
        return A()

    container.register_factory(factory)

    assert isinstance(container.resolve(A), A)
    assert isinstance(container.resolve(Union[A, B]), A)
    assert isinstance(container.resolve(Union[B, A]), A)
    assert isinstance(container.resolve(Optional[A]), A)

    with pytest.raises(ResolutionError):
        container.resolve(B)


# endregion: Union

# region: Optional


def test_optional_provider_optional_query_is_none(container: Container):
    class A:
        pass

    def factory() -> Optional[A]:
        return None

    container.register_factory(factory)
    assert container.resolve(Optional[A]) is None


def test_optional_provider_optional_query_ret_obj(container: Container):
    class A:
        pass

    def factory() -> Optional[A]:
        return A()

    container.register_factory(factory)
    assert isinstance(container.resolve(Optional[A]), A)


def test_optional_provider_non_optional_requester_ret_none(container: Container):
    class A:
        pass

    def factory() -> Optional[A]:
        return None

    container.register_factory(factory)
    with pytest.raises(ResolutionError):
        container.resolve(A)


def test_optional_provider_non_optional_requester_ret_obj(container: Container):
    class A:
        pass

    def factory() -> Optional[A]:
        return A()

    container.register_factory(factory)
    assert isinstance(container.resolve(A), A)


# endregion: Optional

# region Tuple


def test_tuple_instance_resolution(container: Container):
    class A:
        pass

    class B:
        pass

    instance = A(), B()

    container.register_instance(instance)

    resolved = container.resolve(Tuple[A, B])
    assert resolved == instance

    assert container.resolve(A) is instance[0]
    assert container.resolve(B) is instance[1]


def test_factory_of_tuple(container: Container):
    class A:
        pass

    class B:
        pass

    instance_a = A()
    instance_b = B()

    def factory() -> Tuple[A, B]:
        return instance_a, instance_b

    container.register_factory(factory)

    assert container.resolve(Tuple[A, B]) == (instance_a, instance_b)
    assert container.resolve(A) is instance_a
    assert container.resolve(B) is instance_b


def test_tuple_provisioning(container: Container):
    class A:
        pass

    class B:
        pass

    instance_a = A()
    instance_b = B()

    container.register_instance(instance_a)
    container.register_instance(instance_b)

    assert container.resolve(Tuple[A, B]) == (instance_a, instance_b)
    assert container.resolve(Tuple[B, A]) == (instance_b, instance_a)
    assert container.resolve(A) is instance_a
    assert container.resolve(B) is instance_b


# endregion Tuple

# region: Collections


def test_resolve_list_of_instances(container: Container):
    class A:
        pass

    instance1 = A()
    instance2 = A()

    container.register_instance(instance1)
    container.register_instance(instance2)

    expected = [instance2, instance1]

    assert container.get_all_instances(A) == expected
    assert list(container.iter_all_instances(A)) == expected
    assert container.resolve(List[A]) == expected
    assert list(container.resolve(Iterable[A])) == expected


def test_resolve_inheritance_list_instances_by_parent(container: Container):
    class Parent:
        pass

    class A(Parent):
        pass

    class B(Parent):
        pass

    instance_a = A()
    instance_b = B()

    container.register_instance(instance_a)
    container.register_instance(instance_b)

    expected = [instance_b, instance_a]

    assert container.get_all_instances(Parent) == expected
    assert list(container.iter_all_instances(Parent)) == expected
    assert container.resolve(List[Parent]) == expected
    assert list(container.resolve(Iterable[Parent])) == [instance_b, instance_a]


def test_resolve_list_of_singleton_class_instances(container: Container):
    class A:
        pass

    container.register_singleton_class(A)

    singleton_instance = container.resolve(A)

    expected = [singleton_instance]

    assert container.get_all_instances(A) == expected
    assert list(container.iter_all_instances(A)) == expected
    assert container.resolve(List[A]) == expected
    assert list(container.resolve(Iterable[A])) == expected


def test_resolve_list_of_union_instances(container: Container):
    class A:
        pass

    class B:
        pass

    instance_a1 = A()
    instance_a2 = A()
    instance_b1 = B()
    instance_b2 = B()

    container.register_instance(instance_a1)
    container.register_instance(instance_a2)
    container.register_instance(instance_b1)
    container.register_instance(instance_b2)

    expected = [
        instance_a2,
        instance_a1,
        instance_b2,
        instance_b1,
    ]

    query = Union[A, B]
    assert container.get_all_instances(query) == expected
    assert list(container.iter_all_instances(query)) == expected
    assert container.resolve(List[query]) == expected
    assert list(container.resolve(Iterable[query])) == expected


def test_resolve_union_of_lists(container: Container):
    class A:
        pass

    class B:
        pass

    instance_a1 = A()
    instance_a2 = A()
    instance_b1 = B()
    instance_b2 = B()

    container.register_instance(instance_a1)
    container.register_instance(instance_a2)
    container.register_instance(instance_b1)
    container.register_instance(instance_b2)

    assert container.resolve(Union[List[A], List[B]]) == [instance_a2, instance_a1]


def test_list_of_none(container: Container):
    assert container.resolve(List[None]) == [None]


def test_list_of_basic_types(container: Container):
    container.register_instance(1)
    container.register_instance(3.0)
    assert container.resolve(List[Union[int, float]]) == [1, 3.0]


def test_inherited_list(container: Container):
    class A(List[int]):
        pass

    container.register_instance(A((1, 2, 3)))
    assert container.resolve(A) == [1, 2, 3]


def test_args_resolution(container: Container):
    class B:
        pass

    class A:
        def __init__(self, *args: B):
            self.args = args

    instance1 = B()
    instance2 = B()
    container.register_instance(instance1)
    container.register_instance(instance2)
    container.register_class(A)
    assert container.resolve(A).args == (instance2, instance1)


def test_iterable_factory_provides_multiply_instances(container: Container):
    class A:
        pass

    instances = [A() for _ in range(3)]

    def factory() -> Iterable[A]:
        return instances

    container.register_factory(factory)
    assert container.resolve(List[A]) == instances
    assert list(container.resolve(Iterable[A])) == instances
    assert container.get_all_instances(A) == instances
    assert list(container.iter_all_instances(A)) == instances


def test_iterable_factory_of_union_type_provides_multiply_instances(
    container: Container,
):
    class A:
        pass

    class B:
        pass

    a1 = A()
    a2 = A()
    b1 = B()
    b2 = B()

    a_instances = [a1, a2]
    b_instances = [b1, b2]

    def factory() -> Iterable[Union[A, B]]:
        yield a1
        yield b1
        yield a2
        yield b2

    container.register_factory(factory)

    assert container.resolve(List[A]) == a_instances
    assert list(container.resolve(Iterable[A])) == a_instances
    assert container.get_all_instances(A) == a_instances
    assert list(container.iter_all_instances(A)) == a_instances

    assert container.resolve(List[B]) == b_instances
    assert list(container.resolve(Iterable[B])) == b_instances
    assert container.get_all_instances(B) == b_instances
    assert list(container.iter_all_instances(B)) == b_instances

    assert container.resolve(List[Union[A, B]]) == [a1, a2, b1, b2]
    assert container.get_all_instances(Union[A, B]) == [a1, a2, b1, b2]


# endregion: Collections

# region: Any


def test_factory_of_any(container: Container):
    class A:
        pass

    def factory() -> Any:
        return A()

    container.register_factory(factory)
    assert isinstance(container.resolve(A), A)


def test_factory_of_any_generator(container: Container):
    class A:
        pass

    class B:
        pass

    def factory() -> Any:
        yield A()
        yield B()

    container.register_factory(factory)
    assert isinstance(container.resolve(A), A)
    assert isinstance(container.resolve(B), B)


# endregion: Any

# region: Recursion


class A:
    def __init__(self, a: "A"):
        self.a = a


def test_self_recursive_class(container: Container):
    container.register_class(A)
    instance = container.resolve(A)
    assert isinstance(instance, A)
    assert isinstance(instance.a, A)


class ARequiresB:
    def __init__(self, b: "BRequiresA"):
        self.b = b


class BRequiresA:
    def __init__(self, a: ARequiresB):
        self.a = a


def test_circular_dependency_classes(container: Container):
    container.register_class(ARequiresB)
    container.register_class(BRequiresA)

    a_instance = container.resolve(ARequiresB)
    assert isinstance(a_instance, ARequiresB)
    assert isinstance(a_instance.b, BRequiresA)

    b_instance = container.resolve(BRequiresA)
    assert isinstance(b_instance, BRequiresA)
    assert isinstance(b_instance.a, ARequiresB)


def test_circular_dependency_factories(container: Container):
    class A:
        pass

    class B:
        pass

    calls = []

    def factory_of_a(b: B) -> A:
        calls.append("factory_of_a")
        return A()

    def factory_of_b(a: A) -> B:
        calls.append("factory_of_b")
        return B()

    container.register_factory(factory_of_a)
    container.register_factory(factory_of_b)

    a_instance = container.resolve(A)
    assert isinstance(a_instance, A)

    assert calls == ["factory_of_b", "factory_of_a"]

    b_instance = container.resolve(B)
    assert isinstance(b_instance, B)

    assert calls == ["factory_of_b", "factory_of_a", "factory_of_a", "factory_of_b"]


def test_circular_dependency_generator_factories(container: Container):
    class A:
        pass

    class B:
        pass

    class C:
        pass

    calls = []

    def factory1(c: C) -> Iterable[Union[A, B]]:
        calls.append("factory1")
        yield A()
        yield B()

    def factory2(a: A, b: B) -> Iterable[C]:
        calls.append("factory2")
        yield C()

    container.register_factory(factory1)
    container.register_factory(factory2)

    a, b, c = container.resolve(Tuple[A, B, C])

    assert isinstance(a, A)
    assert isinstance(b, B)
    assert isinstance(c, C)

    assert calls == ["factory2", "factory1"]


# endregion
