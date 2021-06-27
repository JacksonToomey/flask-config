from abc import ABC
from abc import abstractmethod
from dataclasses import MISSING
from dataclasses import fields
from os import environ as os_env
from typing import Any
from typing import Callable
from typing import Generic
from typing import Optional
from typing import Protocol
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from celery import Celery
from flask import Flask
from inject import clear_and_configure

from flask_configurer.dependencies import BaseCeleryDependencyBuilder
from flask_configurer.dependencies import BaseDependencyBuilder
from flask_configurer.dependencies import BaseFlaskDependencyBuilder
from flask_configurer.entities import BaseConfig
from flask_configurer.exc import MissingConfigurationError


class Constructable(Protocol):
    def __init__(self, import_name: str) -> None:
        ...


C = TypeVar("C", bound=BaseConfig)
T = TypeVar("T", bound=Constructable)
D = TypeVar("D", bound=BaseDependencyBuilder)
F = TypeVar(
    "F", bound=Union[Callable[["BaseAppFactory[T, D, C]", Flask], None], Callable[["BaseAppFactory[T, D, C]", Celery], None]]
)


def loader(f: F) -> F:
    f._is_loader = True
    return f


class BaseAppFactory(ABC, Generic[T, D, C]):
    app_class: Type[T]
    dependency_builder_class: Type[D]
    _loader_methods: list[str]
    config_class: Type[C]

    def __init_subclass__(cls: Type["BaseAppFactory[T, D, C]"], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)  # type: ignore
        cls._loader_methods = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if attr and getattr(attr, "_is_loader", False) is True:
                cls._loader_methods.append(attr_name)

    def __call__(self, import_name: str, config: Optional[BaseConfig] = None, skip_injection: bool = False) -> T:
        if not config:
            config = self._get_config_from_env()
        app = self._create_app(import_name)
        self._configure_app(app, config)
        self._run_loaders(app)
        if not skip_injection:
            clear_and_configure(self.dependency_builder_class(config), bind_in_runtime=False)
        return app

    def _create_app(self, import_name: str) -> T:
        return self.app_class(import_name)

    def _run_loaders(self, app: T) -> None:
        for method_name in self._loader_methods:
            getattr(self, method_name)(app)

    @abstractmethod
    def _configure_app(self, app: T, config: BaseConfig) -> None:
        ...

    @classmethod
    def _get_config_from_env(cls) -> BaseConfig:
        args: dict[str, Any] = {}
        for field in fields(cls.config_class):
            if field.name in os_env:
                args[field.name] = os_env[field.name]
            elif field.default is MISSING:
                raise MissingConfigurationError(f"Configuration key {field.name} not in env")
        return cast(C, cls.config_class(**args))


class FlaskAppFactory(BaseAppFactory[Flask, BaseFlaskDependencyBuilder, C]):
    app_class = Flask
    dependency_builder_class = BaseFlaskDependencyBuilder

    def _configure_app(self, app: Flask, config: BaseConfig) -> None:
        app.config.from_object(config)


class CeleryAppFactory(BaseAppFactory[Celery, BaseCeleryDependencyBuilder, C]):
    app_class = Celery
    dependency_builder_class = BaseCeleryDependencyBuilder

    def _configure_app(self, app: Celery, config: BaseConfig) -> None:
        app.config_from_object(config)
