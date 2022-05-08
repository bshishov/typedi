from typing import Protocol, runtime_checkable

import pytest

from typedi import Container


@runtime_checkable
class MathOperation(Protocol):
    def do(self, a: int, b: int) -> int:
        pass


class Sum:
    def do(self, a: int, b: int) -> int:
        return a + b


class Multiply:
    def do(self, a: int, b: int) -> int:
        return a * b


@pytest.fixture
def container():
    return Container()


def test_non_runtime_protocol_raises(container: Container):
    class ProtocolWithDecorator(Protocol):
        pass

    with pytest.raises(TypeError):
        container.register_class(ProtocolWithDecorator)


def test_container_resolves_protocol(container: Container):
    container.register_class(Sum)

    assert isinstance(container.resolve(MathOperation), Sum)


def test_container_resolves_all_instances_of_protocol(container: Container):
    sum_op = Sum()
    mul_op = Multiply()

    container.register_instance(sum_op)
    container.register_instance(mul_op)

    operations = container.get_all_instances(MathOperation)
    assert operations == [mul_op, sum_op]
