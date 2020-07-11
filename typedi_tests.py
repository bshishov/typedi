import pytest

from typedi import *


class Dummy:
    pass


class DummyChild(Dummy):
    pass


def test_default_container_exists():
    import typedi
    assert isinstance(typedi.container, Container)


def test_bind_to_instance():
    c = Container()
    instance = Dummy()
    c.bind_to_instance(Dummy, instance)

    assert c.get_instance(Dummy) is instance


def test_get_missing_instance_raises():
    c = Container()

    with pytest.raises(KeyError):
        c.get_instance(Dummy)
