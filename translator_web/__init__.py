"""Local proofreader & translator web package."""

from .service import TranslationResult, translate_and_correct
from . import config

__all__ = ["TranslationResult", "translate_and_correct", "config"]

