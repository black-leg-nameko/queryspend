"""Render one report object for terminal, Markdown, or JSON."""

from queryspend.renderers.json import JsonRenderer
from queryspend.renderers.markdown import MarkdownRenderer
from queryspend.renderers.terminal import TerminalRenderer

__all__ = ["JsonRenderer", "MarkdownRenderer", "TerminalRenderer"]

