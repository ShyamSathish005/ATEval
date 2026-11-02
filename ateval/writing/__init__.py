"""Local, review-first academic writing analysis."""

from .analysis import analyze_text
from .documents import extract_document
from .editing import apply_accepted_suggestions
from .semantic import validate_preservation

__all__ = ["analyze_text", "apply_accepted_suggestions", "extract_document", "validate_preservation"]
