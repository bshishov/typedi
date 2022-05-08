from typing import Tuple, Iterable, Any, Union, List

import pytest

from typedi import Container


@pytest.fixture()
def container():
    return Container()


class A:
    pass


class B:
    pass


class ShouldNotResolve:
    pass


def register_as_separate_instances(container: Container):
    container.register_instance(A())
    container.register_instance(B())
    container.register_instance(ShouldNotResolve())


def register_as_tuple_ab(container: Container):
    tuple_instance = A(), B()
    container.register_instance(tuple_instance)
    container.register_instance(ShouldNotResolve())


def register_as_tuple_ba(container: Container):
    tuple_instance = B(), A()
    container.register_instance(tuple_instance)
    container.register_instance(ShouldNotResolve())


def register_as_factory_of_ab_tuple(container: Container):
    def factory() -> Tuple[A, B]:
        return A(), B()

    container.register_factory(factory)


def register_as_factory_of_ba_tuple(container: Container):
    def factory() -> Tuple[B, A]:
        return B(), A()

    container.register_factory(factory)


def register_as_factory_of_messy_type(container: Container):
    def factory() -> Tuple[A, ShouldNotResolve, B]:
        return A(), ShouldNotResolve(), B()

    container.register_factory(factory)


def register_as_factory_of_list(container: Container):
    def factory() -> List[Union[B, ShouldNotResolve, A]]:
        return [B(), ShouldNotResolve(), A()]

    container.register_factory(factory)


def register_as_factory_of_any_tuple_type(container: Container):
    def factory() -> Any:
        return A(), ShouldNotResolve(), B()

    container.register_factory(factory)


def register_as_ab_generator(container: Container):
    def factory() -> Iterable[Union[A, B, ShouldNotResolve]]:
        yield A()
        yield ShouldNotResolve()
        yield B()

    container.register_factory(factory)


def register_as_separate_factories(container: Container):
    def factory_with_a() -> Any:
        yield ShouldNotResolve()
        yield A()

    def factory_with_b() -> Iterable[Union[B, ShouldNotResolve]]:
        yield B()
        yield B()
        yield ShouldNotResolve()

    container.register_factory(factory_with_a)
    container.register_factory(factory_with_b)


@pytest.mark.parametrize(
    "register_fn",
    [
        register_as_separate_instances,
        register_as_tuple_ab,
        register_as_tuple_ba,
        register_as_factory_of_ab_tuple,
        register_as_factory_of_ba_tuple,
        register_as_factory_of_messy_type,
        register_as_factory_of_list,
        register_as_factory_of_any_tuple_type,
        register_as_ab_generator,
        register_as_separate_factories,
    ],
)
def test_tuple_dynamic_resolution(container: Container, register_fn):
    register_fn(container)

    a, b = container.resolve(Tuple[A, B])
    assert isinstance(a, A)
    assert isinstance(b, B)

    b, a = container.resolve(Tuple[B, A])
    assert isinstance(a, A)
    assert isinstance(b, B)

    assert isinstance(container.resolve(A), A)
    assert isinstance(container.resolve(B), B)

    a, (a2, b2), b = container.resolve(Tuple[A, Tuple[A, B], B])
    assert isinstance(a, A)
    assert isinstance(b, B)
    assert isinstance(a2, A)
    assert isinstance(b2, B)


def test_container_tries_resolve_same_tuple_first(container: Container):
    instance = A(), B()
    container.register_instance(instance)
    assert container.resolve(Tuple[A, B]) is instance
