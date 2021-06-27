from dataclasses import dataclass
from typing import Optional

from flask_configurer.app_factory import BaseAppFactory
from flask_configurer.dependencies import BaseDependencyBuilder
from flask_configurer.entities import BaseConfig


@dataclass
class CustomApp:
    name: str
    config: Optional[BaseConfig] = None


class CustomBuilder(BaseDependencyBuilder):
    config_class = BaseConfig


class CustomFactory(BaseAppFactory[CustomApp, CustomBuilder, BaseConfig]):
    dependency_builder_class = CustomBuilder
    config_class = BaseConfig


def test_factory():
    ...
