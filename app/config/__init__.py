# This file makes 'config' a Python package

from .settings import config, setup_logging
from .christian_rubric import get_christian_rubric

__all__ = ['config', 'setup_logging', 'get_christian_rubric']
