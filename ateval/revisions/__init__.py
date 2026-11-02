"""Human revision data, alignment, intent, and CPU baseline components."""

from .alignment import align_sentences, extract_edit_spans, split_sentences
from .schema import EditSpan, RevisionRecord, validate_record
from .taxonomy import canonical_intent

__all__ = ["EditSpan", "RevisionRecord", "align_sentences", "canonical_intent", "extract_edit_spans", "split_sentences", "validate_record"]
