import pytest
from pydantic import ValidationError

from backend.models import NoteIn, SegmentOverrideIn


def test_note_requires_nonempty_text():
    with pytest.raises(ValidationError):
        NoteIn(note_text="")


def test_note_accepts_text():
    assert NoteIn(note_text="called customer").note_text == "called customer"


def test_segment_override_uppercased():
    assert SegmentOverrideIn(override_segment="s1").override_segment == "S1"


def test_segment_override_requires_value():
    with pytest.raises(ValidationError):
        SegmentOverrideIn(override_segment="")
