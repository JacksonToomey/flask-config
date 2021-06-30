#  type: ignore
from dataclasses import dataclass
from typing import Optional
from unittest.mock import patch

import pytest

from flask_configurer.app_factory import BaseAppFactory
from flask_configurer.app_factory import loader
from flask_configurer.dependencies import BaseDependencyBuilder
from flask_configurer.entities import BaseConfig
from flask_configurer.exc import MissingConfigurationError


@pytest.fixture(name="mock_configure")
def _mock_configure():
    with patch("flask_configurer.app_factory.clear_and_configure") as patched:
        yield patched


@pytest.fixture(name="custom_app_class")
def _app_class():
    @dataclass
    class CustomApp:
        name: str
        config: Optional[BaseConfig] = None
        extension_1: Optional[str] = None
        extension_2: Optional[str] = None

    return CustomApp


@pytest.fixture(name="basic_custom_factory_class")
def _basic_custom_factory_class(custom_app_class):
    class CustomBuilder(BaseDependencyBuilder):
        config_class = BaseConfig

        def __eq__(self, other) -> bool:
            if not isinstance(other, CustomBuilder):
                return False

            return self._config == other._config

    class CustomFactory(BaseAppFactory[custom_app_class, CustomBuilder, BaseConfig]):
        dependency_builder_class = CustomBuilder
        config_class = BaseConfig
        app_class = custom_app_class

        def _configure_app(self, app: app_class, config: BaseConfig) -> None:
            app.config = config

    return CustomFactory


@pytest.fixture(name="loader_custom_factory_class")
def _loader_custom_factory_class(basic_custom_factory_class, custom_app_class):
    class LoaderCustomFactory(basic_custom_factory_class):
        @loader
        def _load_extension_1(self, app: custom_app_class) -> None:
            app.extension_1 = "called_1"

        @loader
        def _load_extension_2(self, app: custom_app_class) -> None:
            app.extension_2 = "called_2"

    return LoaderCustomFactory


@pytest.fixture(name="config_custom_factory_class")
def _config_custom_factory_class(custom_app_class, config_class_with_props):
    class CustomBuilder(BaseDependencyBuilder):
        config_class = config_class_with_props

        def __eq__(self, other) -> bool:
            if not isinstance(other, CustomBuilder):
                return False

            return self._config == other._config

    class CustomFactory(BaseAppFactory[custom_app_class, CustomBuilder, config_class_with_props]):
        dependency_builder_class = CustomBuilder
        config_class = config_class_with_props
        app_class = custom_app_class

        def _configure_app(self, app: app_class, config: config_class_with_props) -> None:
            app.config = config

    return CustomFactory


@pytest.fixture(name="loader_custom_factory")
def _loader_custom_factory(loader_custom_factory_class):
    return loader_custom_factory_class()


@pytest.fixture(name="basic_custom_factory")
def _basic_custom_factory(basic_custom_factory_class):

    return basic_custom_factory_class()


@pytest.fixture(name="config_custom_factory")
def _config_custom_factory(config_custom_factory_class):
    return config_custom_factory_class()


@pytest.fixture(name="mock_env")
def _mock_env():
    mock_env = {"a": "env_a", "b": "env_b", "c": "env_c"}
    with patch("flask_configurer.app_factory.os_env", mock_env):
        yield mock_env


@pytest.fixture(name="config_class_with_props")
def _config_class_with_props():
    @dataclass(frozen=True)
    class ConfigWithProps:
        a: str
        b: str
        c: str = "already_provided"
        d: Optional[str] = None

    return ConfigWithProps


def test_factory_no_config(basic_custom_factory, mock_configure):
    app = basic_custom_factory("some_name")
    assert app.config is not None
    mock_configure.assert_called_once_with(basic_custom_factory.dependency_builder_class(app.config), bind_in_runtime=False)
    assert app.name == "some_name"


def test_factory_with_config(basic_custom_factory, mock_configure):
    config = BaseConfig()
    app = basic_custom_factory("some_name", config)
    assert app.config is config
    mock_configure.assert_called_once_with(basic_custom_factory.dependency_builder_class(config), bind_in_runtime=False)


def test_factory_loader(loader_custom_factory):
    app = loader_custom_factory("some_name")
    assert app.extension_1 == "called_1"
    assert app.extension_2 == "called_2"


@pytest.mark.usefixtures("mock_env")
def test_from_env(config_custom_factory, config_class_with_props):
    app = config_custom_factory("some_name")
    assert app.config == config_class_with_props("env_a", "env_b", "env_c")


@pytest.mark.usefixtures("mock_env")
def test_from_env_with_config(config_custom_factory, config_class_with_props):
    config = config_class_with_props("custom_a", "custom_b")
    app = config_custom_factory("some_name", config)
    assert app.config is config


def test_from_env_missing(config_custom_factory, mock_env):
    mock_env.pop("a")
    with pytest.raises(MissingConfigurationError):
        config_custom_factory("some_name")
