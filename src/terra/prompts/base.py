"""Prompt template utilities."""

from __future__ import annotations

from string import Template
from typing import Any

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """A reusable prompt template with variable substitution.

    Uses Python's string.Template ($variable or ${variable}) syntax
    for simple, safe interpolation.
    """

    name: str
    template: str
    description: str = ""
    variables: list[str] = Field(default_factory=list)

    def render(self, **kwargs: Any) -> str:
        """Render the template with provided variables.

        Args:
            **kwargs: Variable values to substitute.

        Returns:
            Rendered prompt string.

        Raises:
            KeyError: If a required variable is missing.
        """
        tmpl = Template(self.template)
        return tmpl.substitute(**kwargs)

    def safe_render(self, **kwargs: Any) -> str:
        """Render the template, leaving missing variables as placeholders."""
        tmpl = Template(self.template)
        return tmpl.safe_substitute(**kwargs)
