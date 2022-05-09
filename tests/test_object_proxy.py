"""Tests for ObjectProxy class

original implementation by Graham Dumpleton
see: https://github.com/GrahamDumpleton/wrapt/blob/e96b09d7af4e690b1822f8ccc6bf2ea7507bff8f/src/wrapt/wrappers.py

original tests (in unittests) by Graham Dumpleton:
    https://github.com/GrahamDumpleton/wrapt/blob/e96b09d7af4e690b1822f8ccc6bf2ea7507bff8f/tests/test_object_proxy.py

Copyright (c) 2013-2022, Graham Dumpleton
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

import types

import pytest

from typedi.object_proxy import ObjectProxy


OBJECTS_CODE = """
class TargetBaseClass(object):
    "documentation"

class Target(TargetBaseClass):
    "documentation"

def target():
    "documentation"
    pass
"""

objects = types.ModuleType("objects")
exec(OBJECTS_CODE, objects.__dict__, objects.__dict__)


class CallableObjectProxy(ObjectProxy):
    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)


def test_init_not_called():

    a = ObjectProxy.__new__(ObjectProxy)
    b = ObjectProxy.__new__(ObjectProxy)

    try:
        a.__wrapped__
    except ValueError:
        pass

    try:
        a + b
    except ValueError:
        pass


def test_attributes():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    assert function2.__wrapped__ == function1


def test_get_wrapped():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    assert function2.__wrapped__ == function1

    function3 = ObjectProxy(function2)

    assert function3.__wrapped__ == function1


def test_set_wrapped():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    assert function2 == function1
    assert function2.__wrapped__ == function1
    assert function2.__name__ == function1.__name__

    assert function2.__qualname__ == function1.__qualname__

    function2.__wrapped__ = None

    assert not hasattr(function1, "__wrapped__")

    assert function2 == None
    assert function2.__wrapped__ == None
    assert not hasattr(function2, "__name__")

    assert not hasattr(function2, "__qualname__")

    def function3(*args, **kwargs):
        return args, kwargs

    function2.__wrapped__ = function3

    assert function2 == function3
    assert function2.__wrapped__ == function3
    assert function2.__name__ == function3.__name__

    assert function2.__qualname__ == function3.__qualname__


def test_delete_wrapped():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    def run(*args):
        del function2.__wrapped__

    with pytest.raises(TypeError):
        run()


def test_proxy_attribute():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    function2._self_variable = True

    assert not hasattr(function1, "_self_variable")
    assert hasattr(function2, "_self_variable")

    assert function2._self_variable is True

    del function2._self_variable

    assert not hasattr(function1, "_self_variable")
    assert not hasattr(function2, "_self_variable")

    assert getattr(function2, "_self_variable", None) is None


def test_wrapped_attribute():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    function2.variable = True

    assert hasattr(function1, "variable")
    assert hasattr(function2, "variable")

    assert function2.variable == True

    del function2.variable

    assert not hasattr(function1, "variable")
    assert not hasattr(function2, "variable")

    assert getattr(function2, "variable", None) is None


def test_class_object_name():
    # Test preservation of class __name__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    assert wrapper.__name__ == target.__name__


def test_class_object_qualname():
    # Test preservation of class __qualname__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    try:
        __qualname__ = target.__qualname__
    except AttributeError:
        pass
    else:
        assert wrapper.__qualname__ == __qualname__


def test_class_module_name():
    # Test preservation of class __module__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    assert wrapper.__module__ == target.__module__


def test_class_doc_string():
    # Test preservation of class __doc__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    assert wrapper.__doc__ == target.__doc__


def test_instance_module_name():
    # Test preservation of instance __module__ attribute.

    target = objects.Target()
    wrapper = ObjectProxy(target)

    assert wrapper.__module__ == target.__module__


def test_instance_doc_string():
    # Test preservation of instance __doc__ attribute.

    target = objects.Target()
    wrapper = ObjectProxy(target)

    assert wrapper.__doc__ == target.__doc__


def test_function_object_name():
    # Test preservation of function __name__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    assert wrapper.__name__ == target.__name__


def test_function_object_qualname():
    # Test preservation of function __qualname__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    try:
        __qualname__ = target.__qualname__
    except AttributeError:
        pass
    else:
        assert wrapper.__qualname__ == __qualname__


def test_function_module_name():
    # Test preservation of function __module__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    assert wrapper.__module__ == target.__module__


def test_function_doc_string():
    # Test preservation of function __doc__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    assert wrapper.__doc__ == target.__doc__


def test_class_of_class():
    # Test preservation of class __class__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    assert wrapper.__class__ == target.__class__

    assert isinstance(wrapper, type(target))


def test_class_of_instance():
    # Test preservation of instance __class__ attribute.

    target = objects.Target()
    wrapper = ObjectProxy(target)

    assert wrapper.__class__ == target.__class__

    assert isinstance(wrapper, objects.Target)
    assert isinstance(wrapper, objects.TargetBaseClass)


def test_class_of_function():
    # Test preservation of function __class__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    assert wrapper.__class__ == target.__class__

    assert isinstance(wrapper, type(target))


def test_dir_of_class():
    # Test preservation of class __dir__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    assert dir(wrapper) == dir(target)


def test_vars_of_class():
    # Test preservation of class __dir__ attribute.

    target = objects.Target
    wrapper = ObjectProxy(target)

    assert vars(wrapper) == vars(target)


def test_dir_of_instance():
    # Test preservation of instance __dir__ attribute.

    target = objects.Target()
    wrapper = ObjectProxy(target)

    assert dir(wrapper) == dir(target)


def test_vars_of_instance():
    # Test preservation of instance __dir__ attribute.

    target = objects.Target()
    wrapper = ObjectProxy(target)

    assert vars(wrapper) == vars(target)


def test_dir_of_function():
    # Test preservation of function __dir__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    assert dir(wrapper) == dir(target)


def test_vars_of_function():
    # Test preservation of function __dir__ attribute.

    target = objects.target
    wrapper = ObjectProxy(target)

    assert vars(wrapper) == vars(target)


def test_function_no_args():
    _args = ()
    _kwargs = {}

    def function(*args, **kwargs):
        return args, kwargs

    wrapper = CallableObjectProxy(function)

    result = wrapper()

    assert result, _args == _kwargs


def test_function_args():
    _args = (1, 2)
    _kwargs = {}

    def function(*args, **kwargs):
        return args, kwargs

    wrapper = CallableObjectProxy(function)

    result = wrapper(*_args)

    assert result, _args == _kwargs


def test_function_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    def function(*args, **kwargs):
        return args, kwargs

    wrapper = CallableObjectProxy(function)

    result = wrapper(**_kwargs)

    assert result, _args == _kwargs


def test_function_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    def function(*args, **kwargs):
        return args, kwargs

    wrapper = CallableObjectProxy(function)

    result = wrapper(*_args, **_kwargs)

    assert result, _args == _kwargs


def test_instancemethod_no_args():
    _args = ()
    _kwargs = {}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper()

    assert result, _args == _kwargs


def test_instancemethod_args():
    _args = (1, 2)
    _kwargs = {}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(*_args)

    assert result, _args == _kwargs


def test_instancemethod_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(**_kwargs)

    assert result, _args == _kwargs


def test_instancemethod_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(*_args, **_kwargs)

    assert result, _args == _kwargs


def test_instancemethod_via_class_no_args():
    _args = ()
    _kwargs = {}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(Class())

    assert result, _args == _kwargs


def test_instancemethod_via_class_args():
    _args = (1, 2)
    _kwargs = {}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(Class(), *_args)

    assert result, _args == _kwargs


def test_instancemethod_via_class_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(Class(), **_kwargs)

    assert result, _args == _kwargs


def test_instancemethod_via_class_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        def function(self, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(Class(), *_args, **_kwargs)

    assert result, _args == _kwargs


def test_classmethod_no_args():
    _args = ()
    _kwargs = {}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper()

    assert result, _args == _kwargs


def test_classmethod_args():
    _args = (1, 2)
    _kwargs = {}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(*_args)

    assert result, _args == _kwargs


def test_classmethod_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(**_kwargs)

    assert result, _args == _kwargs


def test_classmethod_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(*_args, **_kwargs)

    assert result, _args == _kwargs


def test_classmethod_via_class_no_args():
    _args = ()
    _kwargs = {}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper()

    assert result, _args == _kwargs


def test_classmethod_via_class_args():
    _args = (1, 2)
    _kwargs = {}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(*_args)

    assert result, _args == _kwargs


def test_classmethod_via_class_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(**_kwargs)

    assert result, _args == _kwargs


def test_classmethod_via_class_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @classmethod
        def function(cls, *args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(*_args, **_kwargs)

    assert result, _args == _kwargs


def test_staticmethod_no_args():
    _args = ()
    _kwargs = {}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper()

    assert result, _args == _kwargs


def test_staticmethod_args():
    _args = (1, 2)
    _kwargs = {}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(*_args)

    assert result, _args == _kwargs


def test_staticmethod_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(**_kwargs)

    assert result, _args == _kwargs


def test_staticmethod_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class().function)

    result = wrapper(*_args, **_kwargs)

    assert result, _args == _kwargs


def test_staticmethod_via_class_no_args():
    _args = ()
    _kwargs = {}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper()

    assert result, _args == _kwargs


def test_staticmethod_via_class_args():
    _args = (1, 2)
    _kwargs = {}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(*_args)

    assert result, _args == _kwargs


def test_staticmethod_via_class_kwargs():
    _args = ()
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(**_kwargs)

    assert result, _args == _kwargs


def test_staticmethod_via_class_args_plus_kwargs():
    _args = (1, 2)
    _kwargs = {"one": 1, "two": 2}

    class Class(object):
        @staticmethod
        def function(*args, **kwargs):
            return args, kwargs

    wrapper = CallableObjectProxy(Class.function)

    result = wrapper(*_args, **_kwargs)

    assert result, _args == _kwargs


def test_iteration():
    items = [1, 2]

    wrapper = ObjectProxy(items)

    result = [x for x in wrapper]

    assert result == items


def test_context_manager():
    class Class(object):
        def __enter__(self):
            return self

        def __exit__(*args, **kwargs):
            return

    instance = Class()

    wrapper = ObjectProxy(instance)

    with wrapper:
        pass


def test_object_hash():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    assert hash(function2) == hash(function1)


def test_mapping_key():
    def function1(*args, **kwargs):
        return args, kwargs

    function2 = ObjectProxy(function1)

    table = dict()
    table[function1] = True

    assert table.get(function2)

    table = dict()
    table[function2] = True

    assert table.get(function1)


def test_comparison():
    one = ObjectProxy(1)
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert two > 1
    assert two >= 1
    assert two < 3
    assert two <= 3
    assert two != 1
    assert two == 2
    assert two != 3

    assert 2 > one
    assert 2 >= one
    assert 2 < three
    assert 2 <= three
    assert 2 != one
    assert 2 == two
    assert 2 != three

    assert two > one
    assert two >= one
    assert two < three
    assert two <= three
    assert two != one
    assert two == two
    assert two != three


def test_nonzero():
    true = ObjectProxy(True)
    false = ObjectProxy(False)

    assert true
    assert not false

    assert bool(true)
    assert not bool(false)

    assert not false
    assert not not true


def test_int():
    one = ObjectProxy(1)

    assert int(one) == 1


def test_float():
    one = ObjectProxy(1)

    assert float(one) == 1.0


def test_add():
    one = ObjectProxy(1)
    two = ObjectProxy(2)

    assert one + two == 1 + 2
    assert 1 + two == 1 + 2
    assert one + 2 == 1 + 2


def test_add_uninitialized_args():
    result = object()

    one = ObjectProxy.__new__(ObjectProxy)
    two = ObjectProxy(2)

    try:
        assert one + two == result
    except ValueError:
        pass

    one = ObjectProxy(1)
    two = ObjectProxy.__new__(ObjectProxy)

    try:
        assert one + two == result
    except ValueError:
        pass


def test_sub():
    one = ObjectProxy(1)
    two = ObjectProxy(2)

    assert one - two == 1 - 2
    assert 1 - two == 1 - 2
    assert one - 2 == 1 - 2


def test_sub_uninitialized_args():
    result = object()

    one = ObjectProxy.__new__(ObjectProxy)
    two = ObjectProxy(2)

    try:
        assert one - two == result
    except ValueError:
        pass

    one = ObjectProxy(1)
    two = ObjectProxy.__new__(ObjectProxy)

    try:
        assert one - two == result
    except ValueError:
        pass


def test_mul():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert two * three == 2 * 3
    assert 2 * three == 2 * 3
    assert two * 3 == 2 * 3


def test_mul_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert two * three == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert two * three == result
    except ValueError:
        pass


def test_div():
    # On Python 2 this will pick up div and on Python
    # 3 it will pick up truediv.

    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert two / three == 2 / 3
    assert 2 / three == 2 / 3
    assert two / 3 == 2 / 3


def test_div_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert two / three == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert two / three == result
    except ValueError:
        pass


def test_floordiv():
    two = ObjectProxy(2)
    four = ObjectProxy(4)

    assert four // two == 4 // 2
    assert 4 // two == 4 // 2
    assert four // 2 == 4 // 2


def test_floordiv_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    four = ObjectProxy(4)

    try:
        assert two // four == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    four = ObjectProxy.__new__(ObjectProxy)

    try:
        assert two // four == result
    except ValueError:
        pass


def test_mod():
    two = ObjectProxy(2)
    four = ObjectProxy(4)

    assert four % two == 4 % 2
    assert 4 % two == 4 % 2
    assert four % 2 == 4 % 2


def test_mod_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    four = ObjectProxy(4)

    try:
        assert two % four == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    four = ObjectProxy.__new__(ObjectProxy)

    try:
        assert two % four == result
    except ValueError:
        pass


def test_divmod():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert divmod(three, two) == divmod(3, 2)
    assert divmod(3, two) == divmod(3, 2)
    assert divmod(three, 2) == divmod(3, 2)


def test_divmod_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert divmod(two, three) == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert divmod(two, three) == result
    except ValueError:
        pass


def test_pow():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert three**two == pow(3, 2)
    assert 3**two == pow(3, 2)
    assert three**2 == pow(3, 2)

    assert pow(three, two) == pow(3, 2)
    assert pow(3, two) == pow(3, 2)
    assert pow(three, 2) == pow(3, 2)

    # Only PyPy implements __rpow__ for ternary pow().

    # if is_pypy:
    #   assert pow(three, two, 2) == pow(3, 2, 2)
    #   assert pow(3, two, 2) == pow(3, 2, 2)

    assert pow(three, 2, 2) == pow(3, 2, 2)


def test_pow_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert three**two == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert three**two == result
    except ValueError:
        pass


def test_lshift():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert three << two == 3 << 2
    assert 3 << two == 3 << 2
    assert three << 2 == 3 << 2


def test_lshift_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert three << two == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert three << two == result
    except ValueError:
        pass


def test_rshift():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert three >> two == 3 >> 2
    assert 3 >> two == 3 >> 2
    assert three >> 2 == 3 >> 2


def test_rshift_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert three >> two == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert three >> two == result
    except ValueError:
        pass


def test_and():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert three & two == 3 & 2
    assert 3 & two == 3 & 2
    assert three & 2 == 3 & 2


def test_and_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert three & two == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert three & two == result
    except ValueError:
        pass


def test_xor():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert three ^ two == 3 ^ 2
    assert 3 ^ two == 3 ^ 2
    assert three ^ 2 == 3 ^ 2


def test_xor_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert three ^ two == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert three ^ two == result
    except ValueError:
        pass


def test_or():
    two = ObjectProxy(2)
    three = ObjectProxy(3)

    assert three | two == 3 | 2
    assert 3 | two == 3 | 2
    assert three | 2 == 3 | 2


def test_or_uninitialized_args():
    result = object()

    two = ObjectProxy.__new__(ObjectProxy)
    three = ObjectProxy(3)

    try:
        assert three | two == result
    except ValueError:
        pass

    two = ObjectProxy(2)
    three = ObjectProxy.__new__(ObjectProxy)

    try:
        assert three | two == result
    except ValueError:
        pass


def test_iadd():
    value = ObjectProxy(1)
    one = ObjectProxy(1)

    value += 1
    assert value == 2

    assert type(value) == ObjectProxy

    value += one
    assert value == 3

    assert type(value) == ObjectProxy


def test_isub():
    value = ObjectProxy(1)
    one = ObjectProxy(1)

    value -= 1
    assert value == 0

    assert type(value) == ObjectProxy

    value -= one
    assert value == -1

    assert type(value) == ObjectProxy


def test_imul():
    value = ObjectProxy(2)
    two = ObjectProxy(2)

    value *= 2
    assert value == 4

    assert type(value) == ObjectProxy

    value *= two
    assert value == 8

    assert type(value) == ObjectProxy


def test_idiv():
    # On Python 2 this will pick up div and on Python
    # 3 it will pick up truediv.

    value = ObjectProxy(2)
    two = ObjectProxy(2)

    value /= 2
    assert value == 2 / 2

    assert type(value) == ObjectProxy

    value /= two
    assert value == 2 / 2 / 2

    assert type(value) == ObjectProxy


def test_ifloordiv():
    value = ObjectProxy(2)
    two = ObjectProxy(2)

    value //= 2
    assert value == 2 // 2

    assert type(value) == ObjectProxy

    value //= two
    assert value == 2 // 2 // 2

    assert type(value) == ObjectProxy


def test_imod():
    value = ObjectProxy(10)
    two = ObjectProxy(2)

    value %= 2
    assert value == 10 % 2

    assert type(value) == ObjectProxy

    value %= two
    assert value == 10 % 2 % 2

    assert type(value) == ObjectProxy


def test_ipow():
    value = ObjectProxy(10)
    two = ObjectProxy(2)

    value **= 2
    assert value == 10**2

    assert type(value) == ObjectProxy

    value **= two
    assert value == 10**2**2

    assert type(value) == ObjectProxy


def test_ilshift():
    value = ObjectProxy(256)
    two = ObjectProxy(2)

    value <<= 2
    assert value == 256 << 2

    assert type(value) == ObjectProxy

    value <<= two
    assert value == 256 << 2 << 2

    assert type(value) == ObjectProxy


def test_irshift():
    value = ObjectProxy(2)
    two = ObjectProxy(2)

    value >>= 2
    assert value == 2 >> 2

    assert type(value) == ObjectProxy

    value >>= two
    assert value == 2 >> 2 >> 2

    assert type(value) == ObjectProxy


def test_iand():
    value = ObjectProxy(1)
    two = ObjectProxy(2)

    value &= 2
    assert value == 1 & 2

    assert type(value) == ObjectProxy

    value &= two
    assert value == 1 & 2 & 2

    assert type(value) == ObjectProxy


def test_ixor():
    value = ObjectProxy(1)
    two = ObjectProxy(2)

    value ^= 2
    assert value == 1 ^ 2

    assert type(value) == ObjectProxy

    value ^= two
    assert value == 1 ^ 2 ^ 2

    assert type(value) == ObjectProxy


def test_ior():
    value = ObjectProxy(1)
    two = ObjectProxy(2)

    value |= 2
    assert value == 1 | 2

    assert type(value) == ObjectProxy

    value |= two
    assert value == 1 | 2 | 2

    assert type(value) == ObjectProxy


def test_ior_list_self():
    value = ObjectProxy([])

    try:
        value |= value
    except TypeError:
        pass


def test_neg():
    value = ObjectProxy(1)

    assert -value == -1


def test_pos():
    value = ObjectProxy(1)

    assert +value == 1


def test_abs():
    value = ObjectProxy(-1)

    assert abs(value) == 1


def test_invert():
    value = ObjectProxy(1)

    assert ~value == ~1


def test_oct():
    value = ObjectProxy(20)

    assert oct(value) == oct(20)


def test_hex():
    value = ObjectProxy(20)

    assert hex(value) == hex(20)


def test_index():
    class Class(object):
        def __index__(self):
            return 1

    value = ObjectProxy(Class())
    items = [0, 1, 2]

    assert items[value] == items[1]


def test_length():
    value = ObjectProxy(list(range(3)))

    assert len(value) == 3


def test_contains():
    value = ObjectProxy(list(range(3)))

    assert 2 in value
    assert not -2 in value


def test_getitem():
    value = ObjectProxy(list(range(3)))

    assert value[1] == 1


def test_setitem():
    value = ObjectProxy(list(range(3)))
    value[1] = -1

    assert value[1] == -1


def test_delitem():
    value = ObjectProxy(list(range(3)))

    assert len(value) == 3

    del value[1]

    assert len(value) == 2
    assert value[1] == 2


def test_getslice():
    value = ObjectProxy(list(range(5)))

    assert value[1:4], [1, 2 == 3]


def test_setslice():
    value = ObjectProxy(list(range(5)))

    value[1:4] = reversed(value[1:4])

    assert value[1:4], [3, 2 == 1]


def test_delslice():
    value = ObjectProxy(list(range(5)))

    del value[1:4]

    assert len(value) == 2
    assert value, [0 == 4]


def test_dict_length():
    value = ObjectProxy(dict.fromkeys(range(3), False))

    assert len(value) == 3


def test_dict_contains():
    value = ObjectProxy(dict.fromkeys(range(3), False))

    assert 2 in value
    assert not -2 in value


def test_dict_getitem():
    value = ObjectProxy(dict.fromkeys(range(3), False))

    assert value[1] == False


def test_dict_setitem():
    value = ObjectProxy(dict.fromkeys(range(3), False))
    value[1] = True

    assert value[1] == True


def test_dict_delitem():
    value = ObjectProxy(dict.fromkeys(range(3), False))

    assert len(value) == 3

    del value[1]

    assert len(value) == 2


def test_str():
    value = ObjectProxy(10)

    assert str(value) == str(10)

    value = ObjectProxy((10,))

    assert str(value) == str((10,))

    value = ObjectProxy([10])

    assert str(value) == str([10])

    value = ObjectProxy({10: 10})

    assert str(value) == str({10: 10})


def test_repr():
    number = 10
    value = ObjectProxy(number)

    assert repr(value).find("ObjectProxy at") != -1


def test_derived_new():
    class DerivedObjectProxy(ObjectProxy):
        def __new__(cls, wrapped):
            instance = super(DerivedObjectProxy, cls).__new__(cls)
            instance.__init__(wrapped)

        def __init__(self, wrapped):
            super(DerivedObjectProxy, self).__init__(wrapped)

    def function():
        pass

    obj = DerivedObjectProxy(function)


def test_derived_setattr():
    class DerivedObjectProxy(ObjectProxy):
        def __init__(self, wrapped):
            self._self_attribute = True
            super(DerivedObjectProxy, self).__init__(wrapped)

    def function():
        pass

    obj = DerivedObjectProxy(function)


def test_derived_missing_init():
    class DerivedObjectProxy(ObjectProxy):
        def __init__(self, wrapped):
            self.__wrapped__ = wrapped

    def function():
        pass

    obj = DerivedObjectProxy(function)

    assert function == obj
    assert function == obj.__wrapped__


def test_setup_class_attributes():
    def function():
        pass

    class DerivedObjectProxy(ObjectProxy):
        pass

    obj = DerivedObjectProxy(function)

    DerivedObjectProxy.ATTRIBUTE = 1

    assert obj.ATTRIBUTE == 1
    assert not hasattr(function, "ATTRIBUTE")

    del DerivedObjectProxy.ATTRIBUTE

    assert not hasattr(DerivedObjectProxy, "ATTRIBUTE")
    assert not hasattr(obj, "ATTRIBUTE")
    assert not hasattr(function, "ATTRIBUTE")


def test_override_class_attributes():
    def function():
        pass

    class DerivedObjectProxy(ObjectProxy):
        ATTRIBUTE = 1

    obj = DerivedObjectProxy(function)

    assert DerivedObjectProxy.ATTRIBUTE == 1
    assert obj.ATTRIBUTE == 1

    obj.ATTRIBUTE = 2

    assert DerivedObjectProxy.ATTRIBUTE == 1

    assert obj.ATTRIBUTE == 2
    assert not hasattr(function, "ATTRIBUTE")

    del DerivedObjectProxy.ATTRIBUTE

    assert not hasattr(DerivedObjectProxy, "ATTRIBUTE")
    assert obj.ATTRIBUTE == 2
    assert not hasattr(function, "ATTRIBUTE")


def test_class_properties():
    def function():
        pass

    class DerivedObjectProxy(ObjectProxy):
        def __init__(self, wrapped):
            super(DerivedObjectProxy, self).__init__(wrapped)
            self._self_attribute = 1

        @property
        def ATTRIBUTE(self):
            return self._self_attribute

        @ATTRIBUTE.setter
        def ATTRIBUTE(self, value):
            self._self_attribute = value

        @ATTRIBUTE.deleter
        def ATTRIBUTE(self):
            del self._self_attribute

    obj = DerivedObjectProxy(function)

    assert obj.ATTRIBUTE == 1

    obj.ATTRIBUTE = 2

    assert obj.ATTRIBUTE == 2
    assert not hasattr(function, "ATTRIBUTE")

    del obj.ATTRIBUTE

    assert not hasattr(obj, "ATTRIBUTE")
    assert not hasattr(function, "ATTRIBUTE")

    obj.ATTRIBUTE = 1

    assert obj.ATTRIBUTE == 1

    obj.ATTRIBUTE = 2

    assert obj.ATTRIBUTE == 2
    assert not hasattr(function, "ATTRIBUTE")

    del obj.ATTRIBUTE

    assert not hasattr(obj, "ATTRIBUTE")
    assert not hasattr(function, "ATTRIBUTE")


def test_attr_functions():
    def function():
        pass

    proxy = ObjectProxy(function)

    assert hasattr(proxy, "__getattr__")
    assert hasattr(proxy, "__setattr__")
    assert hasattr(proxy, "__delattr__")


def test_override_getattr():
    def function():
        pass

    accessed = []

    class DerivedObjectProxy(ObjectProxy):
        def __getattr__(self, name):
            accessed.append(name)
            try:
                __getattr__ = super(DerivedObjectProxy, self).__getattr__
            except AttributeError as e:
                raise RuntimeError(str(e))
            return __getattr__(name)

    function.attribute = 1

    proxy = DerivedObjectProxy(function)

    assert proxy.attribute == 1

    assert "attribute" in accessed


def test_proxy_hasattr_call():
    proxy = ObjectProxy(None)

    assert not hasattr(proxy, "__call__")


def test_proxy_getattr_call():
    proxy = ObjectProxy(None)

    assert getattr(proxy, "__call__", None) is None


def test_proxy_is_callable():
    proxy = ObjectProxy(None)

    assert not callable(proxy)


def test_callable_proxy_hasattr_call():
    proxy = CallableObjectProxy(None)

    assert hasattr(proxy, "__call__")


def test_callable_proxy_getattr_call():
    proxy = CallableObjectProxy(None)

    assert getattr(proxy, "__call__", None), None


def test_callable_proxy_is_callable():
    proxy = CallableObjectProxy(None)

    assert callable(proxy)


def test_class_bytes():
    class Class(object):
        def __bytes__(self):
            return b"BYTES"

    instance = Class()

    proxy = ObjectProxy(instance)

    assert bytes(instance) == bytes(proxy)


def test_str_format():
    instance = "abcd"

    proxy = ObjectProxy(instance)

    assert format(instance, ""), format(proxy == "")


def test_list_reversed():
    instance = [1, 2]

    proxy = ObjectProxy(instance)

    assert list(reversed(instance)) == list(reversed(proxy))


def test_complex():
    instance = 1.0 + 2j

    proxy = ObjectProxy(instance)

    assert complex(instance) == complex(proxy)


def test_decimal_complex():
    import decimal

    instance = decimal.Decimal(123)

    proxy = ObjectProxy(instance)

    assert complex(instance) == complex(proxy)


def test_fractions_round():
    import fractions

    instance = fractions.Fraction("1/2")

    proxy = ObjectProxy(instance)

    assert round(instance) == round(proxy)
