import pytest

from typedi import *


class Dummy:
    pass


class DummyChild(Dummy):
    pass


class NotADummyChild:
    pass


@pytest.fixture
def basic_container() -> Container:
    return Container()


def test_default_container_exists():
    import typedi
    assert isinstance(typedi.container, Container)


def test_bind_to_instance(basic_container: Container):
    instance = Dummy()
    basic_container.register_instance(Dummy, instance)

    assert basic_container.get_instance(Dummy) is instance


def test_get_missing_instance_raises(basic_container: Container):
    with pytest.raises(KeyError):
        basic_container.get_instance(Dummy)


def test_bind_to_factory(basic_container: Container):
    dummy_instance = Dummy()

    def factory():
        return dummy_instance

    basic_container.register_factory(Dummy, factory)

    assert basic_container.get_instance(Dummy) is dummy_instance


def test_bind_child_to_class(basic_container: Container):
    basic_container.register_class(Dummy, DummyChild)
    assert isinstance(basic_container.get_instance(Dummy), DummyChild)


def test_bind_class_not_a_subclass_raises(basic_container: Container):
    with pytest.raises(TypeError):
        basic_container.register_class(Dummy, NotADummyChild)


def test_bind_child_to_instance(basic_container: Container):
    instance = DummyChild()
    basic_container.register_instance(Dummy, instance)
    assert basic_container.get_instance(Dummy) is instance


def test_bind_invalid_instance_raises(basic_container: Container):
    instance = NotADummyChild()
    with pytest.raises(TypeError):
        basic_container.register_class(Dummy, instance)


def test_instance_in_parent_container_accessible_from_child():
    parent = Container()
    child = parent.make_child_container()
    instance_in_parent = Dummy()
    parent.register_instance(Dummy, instance_in_parent)
    assert child.get_instance(Dummy) is instance_in_parent


def test_instance_in_child_container_not_accessible_from_parent():
    parent = Container()
    child = parent.make_child_container()
    instance_in_child = Dummy()
    child.register_instance(Dummy, instance_in_child)
    with pytest.raises(KeyError):
        assert parent.get_instance(Dummy)


def test_singleton_factory(basic_container: Container):
    def factory_fn_that_called_once() -> Dummy:
        return Dummy()

    basic_container.register_singleton_factory(Dummy, factory_fn_that_called_once)

    dummy1 = basic_container.get_instance(Dummy)
    dummy2 = basic_container.get_instance(Dummy)
    assert dummy1 is dummy2


def test_singleton_class(basic_container: Container):
    basic_container.register_singleton_class(Dummy, DummyChild)

    dummy1 = basic_container.get_instance(Dummy)
    dummy2 = basic_container.get_instance(Dummy)
    assert dummy1 is dummy2
    assert isinstance(dummy1, DummyChild)


def test_singleton_class_self(basic_container: Container):
    basic_container.register_singleton_class(Dummy)

    dummy1 = basic_container.get_instance(Dummy)
    dummy2 = basic_container.get_instance(Dummy)
    assert dummy1 is dummy2
    assert isinstance(dummy1, Dummy)
