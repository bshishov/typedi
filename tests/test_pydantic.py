from typedi import Container

import pytest

try:
    from pydantic import BaseModel
except ImportError:
    pytest.skip("Skipping Pydantic tests", allow_module_level=True)


class B(BaseModel):
    pass


class A(BaseModel):
    b: B


def test_simple_pydantic_dependency():
    container = Container()
    container.register_factory(A)
    container.register_factory(B)

    instance = container.resolve(A)
    assert isinstance(instance, A)
    assert isinstance(instance.b, B)
    assert instance.json() == '{"b": {}}'
