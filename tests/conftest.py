from dataclasses import dataclass
from typing import Optional

from inject import clear
import pytest

from flask_configurer.entities import BaseConfig


@dataclass(frozen=True)
class TestConfig(BaseConfig):
    required_string: str
    required_int: int
    default_string: str = "default"
    optional_int: Optional[int] = None


@pytest.fixture(name="config_class")
def _config_class():
    return TestConfig


@pytest.fixture(autouse=True)
def _clear_config():
    yield
    clear()
