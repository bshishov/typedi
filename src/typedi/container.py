from typing import (
    Iterable,
    Any,
    Dict,
    List,
    Union,
    Generic,
    TypeVar,
    Callable,
    Optional,
    Tuple,
    Type,
)
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import inspect
import warnings

from typedi.object_proxy import ObjectProxy
from typedi.typing_utils import (
    get_return_type,
    type_forward_ref_scope,
    eval_type,
    ForwardRef,
)
from typedi.resolution import *

__all__ = ["Container"]


T = TypeVar("T")


class CachedStorage:
    def __init__(self) -> None:
        self.providers_index: Dict[
            TerminalType[Any], List["InstanceProvider[Any]"]
        ] = defaultdict(list)

    def add(self, provider: "InstanceProvider[Any]") -> None:
        for terminal_type in provider.get_type().iterate_possible_terminal_types():
            self.providers_index[terminal_type].append(provider)

    def query(self, type_: TerminalType[T]) -> Iterable["InstanceProvider[T]"]:
        for provider in reversed(self.providers_index[type_]):
            yield provider


class InstanceResolver(IInstanceResolver):
    __slots__ = "_storage", "_instances_cache"

    def __init__(self, storage: CachedStorage) -> None:
        self._storage = storage
        self._provider_results_cache: Dict[InstanceProvider[Any], object] = {}

    def resolve_single_instance(self, type_: "TerminalType[T]") -> T:
        for instance in self.iterate_instances(type_):
            return instance
        raise ResolutionError(type_)

    def iterate_instances(self, type_: "TerminalType[T]") -> Iterable[T]:
        for provider in self._storage.query(type_):
            # To reduce calls to expensive providers
            # We simply cache results of .get_instance() calls
            if provider in self._provider_results_cache:
                provider_result = self._provider_results_cache[provider]
            else:
                # Creating instance could result in recursive calls to iterate_instances.
                # Firstly, we create a proxy object and cache it such that recursive call
                # will hit the cache and use it for further evaluation.
                # It is sort of pre-allocation of the object.
                proxy = ObjectProxy.__new__(ObjectProxy)
                self._provider_results_cache[provider] = proxy

                # Then, we construct an actual genuine instance.
                # Factories and object __init__ methods are called inside.
                provider_result = provider.get_instance(self)

                # Generators need a special treatment.
                # Since provided instances could be used multiple times
                # in order to cache them we need to evaluate them first
                # making cache idempotent.
                if inspect.isgenerator(provider_result):
                    provider_result = tuple(provider_result)

                # Once real instance is created we can initialize proxy and make it behave exactly as
                # original instance (see ObjectProxy implementation)
                proxy.__init__(provider_result)

                # Put actual result in cache so that nobody will use proxies anymore
                self._provider_results_cache[provider] = provider_result

            # Not all instances match the query.
            # i.e. Provider is f() -> Union[A, B], and request type is just A
            for instance in filter_instances_of_terminal_type(provider_result, type_):
                yield instance


def filter_instances_of_terminal_type(
    obj: object, type_: TerminalType[T]
) -> Iterable[T]:
    if type_.type_check_object(obj):
        yield obj  # type: ignore
    elif hasattr(obj, "__iter__"):
        for item in obj:  # type: ignore
            yield from filter_instances_of_terminal_type(item, type_)


class Container:
    __slots__ = "_storage"

    def __init__(self) -> None:
        self._storage = CachedStorage()

        # Register self, so that client code can access the instance of a container
        self.register_instance(self)

    def register_instance(self, instance: object) -> None:
        self._storage.add(ConstInstanceProvider(instance))

    def register_factory(self, factory: Callable[..., Any]) -> None:
        self._storage.add(FactoryInstanceProvider(factory))

    def register_class(self, cls: type) -> None:
        self.register_factory(cls)

    def register_singleton_factory(self, factory: Callable[..., Any]) -> None:
        self._storage.add(SingletonInstanceProvider(FactoryInstanceProvider(factory)))

    def register_singleton_class(self, cls: type) -> None:
        self.register_singleton_factory(cls)

    def resolve(self, query: Type[T]) -> T:
        """Resolves instance (or collection of instances) of specified query.

        Examples:

            resolve(A)
                Will find the latest registered instance of type A
                or raise ResolutionError if resolution is not possible

            resolve(Union[A, B])
                Will find instance of either type A or B
                (resolution performs left to right)
                or raise ResolutionError if resolution is not possible

            resolve(Optional[A])
                Same as resolve(Union[A, None])
                Will try to find the latest registered instance of type A
                or return None (a valid instance of type(None))

            resolve(List[A])
                Will resolve into a list by performing resolution of A.
                If there are no instances of A returns an empty list.

            resolve(Iterable[A])
                Will resolve into an iterator by performing resolution of A.
                If there are no instances of A returns an empty iterable.

        :param: query: Query to resolve.
        :raises: ResolutionError: When container is unable to resolve the query
        :returns: Resolved instance or collection
        """
        meta_type = python_type_to_meta(query)
        return meta_type.resolve_single_instance(InstanceResolver(self._storage))

    def get_all_instances(self, query: Type[T]) -> List[T]:
        meta_type = python_type_to_meta(query)
        return list(
            meta_type.iterate_resolved_instances(InstanceResolver(self._storage))
        )

    def iter_all_instances(self, query: Type[T]) -> Iterable[T]:
        meta_type = python_type_to_meta(query)
        return meta_type.iterate_resolved_instances(InstanceResolver(self._storage))

    def get_instance(self, query: Type[T]) -> T:
        warnings.warn(
            ".get_instance() method is deprecated, use .resolve() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.resolve(query)


class InstanceProvider(Generic[T], metaclass=ABCMeta):
    @abstractmethod
    def get_instance(self, resolver: IInstanceResolver) -> T:
        pass

    @abstractmethod
    def get_type(self) -> MetaType[T]:
        pass


class ConstInstanceProvider(InstanceProvider[T]):
    __slots__ = "_instance"

    def __init__(self, instance: T):
        self._instance = instance

    def get_instance(self, resolver: IInstanceResolver) -> T:
        return self._instance

    def get_type(self) -> MetaType[T]:
        return ClassType[T](type(self._instance))

    def __hash__(self) -> int:
        return hash(("ConstInstanceProvider", id(self._instance)))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ConstInstanceProvider)
            and self._instance == other._instance
        )


class FactoryInstanceProvider(InstanceProvider[T]):
    __slots__ = "_factory", "_annotations", "_eval_scope", "_proxy_recursion_guard"

    def __init__(self, factory: Callable[..., T]):
        self._factory = factory
        self._annotations = self._build_annotations()
        self._eval_scope = type_forward_ref_scope(get_return_type(factory))
        self._proxy_recursion_guard: Optional[ObjectProxy] = None

    def get_type(self) -> MetaType[T]:
        return python_type_to_meta(get_return_type(self._factory))

    def _build_annotations(self) -> Dict[str, Tuple[Any, bool, bool]]:
        annotations = {}

        signature = inspect.signature(self._factory)

        for param_name, param in signature.parameters.items():
            param_annotation = param.annotation
            has_default = param.default is not inspect.Parameter.empty
            is_var_positional = param.kind == inspect.Parameter.VAR_POSITIONAL

            # **kwargs are not supported. They are assumed to be optional by design.
            # So we can just skip resolution
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            if param_annotation is inspect.Parameter.empty:
                if not has_default:
                    raise TypeError(
                        f"Missing annotation (or default) for parameter '{param_name}' of {self._factory}. "
                        f"Container won't be able to resolve this type."
                    )
            else:
                # If param_annotation is a string - it is (in most cases) a ForwardRef.
                # So performing explicit conversion ForwardRef for _eval_type to evaluate it later
                if isinstance(param_annotation, str):
                    param_annotation = ForwardRef(param_annotation)

                annotations[param_name] = (
                    param_annotation,
                    is_var_positional,
                    has_default,
                )
        return annotations

    def get_instance(self, resolver: IInstanceResolver) -> T:
        args: Tuple[Any, ...] = tuple()
        kwargs = {}

        for param_name, (
            param_annotation,
            is_var_positional,
            has_default,
        ) in self._annotations.items():
            # ForwardRef evaluation for module-level declarations in the same module as the user class
            param_annotation = python_type_to_meta(
                eval_type(param_annotation, globals(), self._eval_scope)
            )

            try:
                if is_var_positional:
                    args = tuple(param_annotation.iterate_resolved_instances(resolver))
                else:
                    kwargs[param_name] = param_annotation.resolve_single_instance(
                        resolver
                    )
            except ResolutionError:
                if not has_default:
                    # There is no default for this parameter and container was unable to resolve the type.
                    # Which means that it is not possible to construct the instance.
                    # So, just re-raising the exception.
                    raise

        return self._factory(*args, **kwargs)

    def __hash__(self) -> int:
        return hash(("FactoryInstanceProvider", self._factory))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FactoryInstanceProvider)
            and self._factory == other._factory
        )


class SingletonInstanceProvider(InstanceProvider[T]):
    __slots__ = "_provider", "_instance"

    def __init__(self, provider: InstanceProvider[T]):
        self._provider = provider
        self._instance: Union[T, None] = None

    def get_instance(self, resolver: InstanceResolver) -> T:
        if self._instance is None:
            self._instance = self._provider.get_instance(resolver)
        return self._instance

    def get_type(self) -> MetaType[T]:
        return self._provider.get_type()

    def __hash__(self) -> int:
        return hash(("SingletonInstanceProvider", self._provider))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SingletonInstanceProvider)
            and self._provider == other._provider
        )
