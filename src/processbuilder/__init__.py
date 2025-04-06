"""
Process Builder - A tool for building structured process definitions through interactive interviews.
"""

__version__ = "0.1.0"

from .models import ProcessStep, ProcessNote
from .builder import ProcessBuilder
from .config import Config 