from dataclasses import dataclass
from threading import local
from typing import Any

from inject import Binder
from inject import clear_and_configure
from inject import instance
import pytest

from flask_configurer.dependencies import BaseDependencyBuilder
from flask_configurer.dependencies import bind_to_request
from flask_configurer.dependencies import binder
from flask_configurer.entities import BaseConfig


@dataclass(frozen=True)
class CustomConfig(BaseConfig):
    ...


class Singleton:
    ...


class NonSingleton:
    ...


class PerRequest:
    ...


class BadBuilder(BaseDependencyBuilder):
    config_class = CustomConfig

    @binder
    def _bind_deps(self, binder: Binder) -> None:
        binder.bind_to_provider(PerRequest, self._provide_req)

    @bind_to_request
    def _provide_req(self) -> PerRequest:
        return PerRequest()


class CustomBuilder(BaseDependencyBuilder):
    config_class = CustomConfig
    _context: Any = local()

    @property
    def context(self) -> dict[str, Any]:
        return self._context

    @binder
    def _bind_deps(self, binder: Binder) -> None:
        binder.bind(Singleton, Singleton())
        binder.bind_to_provider(NonSingleton, NonSingleton)
        binder.bind_to_provider(PerRequest, self._provide_req)

    @bind_to_request
    def _provide_req(self) -> PerRequest:
        return PerRequest()


@pytest.fixture(name="config")
def _config():
    return CustomConfig()


@pytest.fixture(autouse=True)
def _inject(config):
    clear_and_configure(CustomBuilder(config))


@pytest.fixture(autouse=True)
def _clear_locals():
    yield
    CustomBuilder._context = local()


def test_subclass_builder_config(config):
    assert instance(CustomConfig) is config


def test_subclass_builder_scope():
    assert instance(Singleton) is instance(Singleton)
    assert instance(NonSingleton) is not instance(NonSingleton)


def test_subclass_builder_custom_scope():
    per_request = instance(PerRequest)
    assert per_request is instance(PerRequest)
    CustomBuilder._context = local()
    assert per_request is not instance(PerRequest)


def test_raises_error(config):
    clear_and_configure(BadBuilder(config))
    with pytest.raises(NotImplementedError):
        instance(PerRequest)
