"""Unit tests for answer_key_parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.answer_key_parser import AnswerKeyParseError, parse_answer_key

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.mark.smoke
def test_parses_test_key_csv():
    data = (FIXTURES / "test_key.csv").read_bytes()
    entries = parse_answer_key(data, "test_key.csv")
    assert entries == [(1, "A"), (2, "B"), (3, "C")]


def test_rejects_invalid_option():
  data = b"question_no,correct_option\n1,X\n"
  with pytest.raises(AnswerKeyParseError, match="Invalid option"):
      parse_answer_key(data, "bad.csv")


def test_digit_mapping():
    data = b"question_no,correct_option\n1,1\n2,2\n"
    entries = parse_answer_key(data, "digits.csv")
    assert entries == [(1, "A"), (2, "B")]


def test_column_alias_tolerance():
    data = b"question_no,correct_option\n5,D\n"
    entries = parse_answer_key(data, "aliases.csv")
    assert entries == [(5, "D")]


def test_empty_file_raises():
    with pytest.raises(AnswerKeyParseError, match="empty"):
        parse_answer_key(b"", "empty.csv")
