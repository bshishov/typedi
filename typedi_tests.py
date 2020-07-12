import pytest

from typedi import *


class Dummy:
    pass


class DummyChild(Dummy):
    pass


class NotADummyChild:
    pass


@pytest.fixture
def basic_container():
    return Container()


def test_default_container_exists():
    import typedi
    assert isinstance(typedi.container, Container)


def test_bind_to_instance(basic_container):
    instance = Dummy()
    basic_container.bind_to_instance(Dummy, instance)

    assert basic_container.get_instance(Dummy) is instance


def test_get_missing_instance_raises(basic_container):
    with pytest.raises(KeyError):
        basic_container.get_instance(Dummy)


def test_bind_to_factory(basic_container):
    dummy_instance = Dummy()

    def factory():
        return dummy_instance

    basic_container.bind_to_factory(Dummy, factory)

    assert basic_container.get_instance(Dummy) is dummy_instance


def test_bind_child_to_class(basic_container):
    basic_container.bind_to_class(Dummy, DummyChild)
    assert isinstance(basic_container.get_instance(Dummy), DummyChild)


def test_bind_class_not_a_subclass_raises(basic_container):
    with pytest.raises(TypeError):
        basic_container.bind_to_class(Dummy, NotADummyChild)


def test_bind_child_to_instance(basic_container):
    instance = DummyChild()
    basic_container.bind_to_instance(Dummy, instance)
    assert basic_container.get_instance(Dummy) is instance


def test_bind_invalid_instance_raises(basic_container):
    instance = NotADummyChild()
    with pytest.raises(TypeError):
        basic_container.bind_to_class(Dummy, instance)


def test_instance_in_parent_container_accessible_from_child():
    parent = Container()
    child = parent.make_child_container()
    instance_in_parent = Dummy()
    parent.bind_to_instance(Dummy, instance_in_parent)
    assert child.get_instance(Dummy) is instance_in_parent


def test_instance_in_child_container_not_accessible_from_parent():
    parent = Container()
    child = parent.make_child_container()
    instance_in_child = Dummy()
    child.bind_to_instance(Dummy, instance_in_child)
    with pytest.raises(KeyError):
        assert parent.get_instance(Dummy)
