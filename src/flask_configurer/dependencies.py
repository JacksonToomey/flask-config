from typing import Any
from typing import Callable
from typing import Type
from typing import TypeVar

from inject import Binder

from flask_configurer.entities import BaseConfig


F = TypeVar("F", bound=Callable[["BaseDependencyBuilder", Binder], None])
B = TypeVar("B", bound=Callable[["BaseDependencyBuilder"], Any])


class BaseDependencyBuilder:
    _binder_methods: list[str]

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

    def __init__(self, config: BaseConfig) -> None:
        self._config = config

    def __call__(self, binder: Binder) -> None:
        for method_name in self._binder_methods:
            getattr(self, method_name)(binder)
