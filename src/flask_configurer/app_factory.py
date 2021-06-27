from abc import ABC
from abc import abstractmethod
from dataclasses import MISSING
from dataclasses import fields
from os import environ as os_env
from typing import Any
from typing import Callable
from typing import Generic
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from celery import Celery
from flask import Flask
from inject import clear_and_configure

from flask_configurer.dependencies import BaseDependencyBuilder
from flask_configurer.entities import BaseConfig
from flask_configurer.exc import MissingConfigurationError


T = TypeVar("T", bound=Union[Flask, Celery])
D = TypeVar("D", bound=BaseDependencyBuilder)
F = TypeVar(
    "F", bound=Union[Callable[["BaseAppFactory[T, D, C]", Flask], None], Callable[["BaseAppFactory[T, D, C]", Celery], None]]
)
C = TypeVar("C", bound=BaseConfig)


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
        return cast(T, self.app_class(import_name))

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


# class AttatchedError(Protocol):
#     exc: ValidationError


# class FlaskAppFactory(BaseAppFactory[Flask, FlaskDependencyBuilder]):
#     app_class = Flask
#     dependency_builder_class = FlaskDependencyBuilder
#
#     def _configure_app(self, app: Flask, config: BaseConfig) -> None:
#         app.config.from_object(config)
#
#     @loader
#     def _load_extensions(self, app: Flask) -> None:
#         csrf.init_app(app)
#         api = Api(app)
#         api.register_blueprint(login_bp, url_prefix="/auth")
#         api.register_blueprint(api_bp, url_prefix="/api")
#
#         @app.context_processor
#         def _context() -> dict[str, Any]:
#             return dict(user=g.get("user", None))
#
#         @app.before_first_request
#         def _load_db() -> None:
#             engine = instance(Engine)
#             META_DATA.create_all(engine)
#
#             session = instance(Session)
#             user = session.query(User).first()
#             if not user:
#                 session.add(User(email="1", password="2"))
#                 session.commit()
#
#     @loader
#     def _load_error_handlers(self, app: Flask) -> None:
#         @app.errorhandler(403)
#         def _handle_forbidden(_: Exception) -> tuple[Response, int]:
#             return jsonify({}), 403
#
#         @app.errorhandler(422)  # type: ignore
#         def _handle_validation_error(e: UnprocessableEntity) -> tuple[Response, int]:
#             err = cast(AttatchedError, e)
#             ve = err.exc
#             messages = cast(dict[str, Any], ve.messages)
#             return jsonify(messages.get("json", {})), 422
#
#
# class CeleryAppFactory(BaseAppFactory[Celery, CeleryDependencyBuilder]):
#     app_class = Celery
#     dependency_builder_class = CeleryDependencyBuilder
#
#     def _configure_app(self, app: Celery, config: BaseConfig) -> None:
#         app.config_from_object(config)
#
#     @loader
#     def _load_tasks(self, app: Celery) -> None:
#         register_tasks(app)
