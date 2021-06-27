from functools import wraps
from typing import Any
from typing import Callable
from typing import Protocol
from typing import Type
from typing import TypeVar
from typing import cast

from celery import current_task
from flask import g
from inject import Binder

from flask_configurer.entities import BaseConfig


F = TypeVar("F", bound=Callable[[Any, Binder], None])
B = TypeVar("B", bound=Callable[[Any], Any])


class BuilderFunction(Protocol):
    _is_binder: bool
    __call__: Callable[[Any, Binder], None]


def bind_to_request(f: B) -> B:
    @wraps(f)
    def _wrapped(self: "BaseDependencyBuilder") -> Any:
        key = f.__name__
        context = self.context
        if not hasattr(context, key):
            val = f(self)
            setattr(context, key, val)
        return getattr(context, key)

    return cast(B, _wrapped)


def binder(f: Callable[[Any, Binder], None]) -> BuilderFunction:
    func = cast(BuilderFunction, f)
    func._is_binder = True
    return func


class BaseDependencyBuilder:
    _binder_methods: list[str]
    config_class: Type[BaseConfig]

    def __init__(self, config: BaseConfig) -> None:
        self._config = config

    @property
    def context(self) -> Any:
        raise NotImplementedError("Builder should implement a context object")

    def __init_subclass__(cls: Type["BaseDependencyBuilder"], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)  # type: ignore
        cls._binder_methods = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if getattr(attr, "_is_binder", False) is True:
                cls._binder_methods.append(attr_name)

    def __call__(self, binder: Binder) -> None:
        for method_name in self._binder_methods:
            getattr(self, method_name)(binder)

    @binder
    def _bind_config(self, binder: Binder) -> None:
        binder.bind(self.config_class, self._config)


class BaseFlaskDependencyBuilder(BaseDependencyBuilder):
    @property
    def context(self) -> Any:
        return g  # pragma: no cover


class BaseCeleryDependencyBuilder(BaseDependencyBuilder):
    @property
    def context(self) -> Any:
        return current_task.request  # pragma: no cover
