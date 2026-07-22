"""Student roster parser unit tests."""

from __future__ import annotations

import pytest

from app.services.student_parser import StudentParseError, parse_students


@pytest.mark.unit
def test_parse_csv_with_headers():
    data = b"roll_no,name,class_section\n1001,Alice,A\n1002,Bob,B\n"
    entries = parse_students(data, "roster.csv")
    assert len(entries) == 2
    assert entries[0] == ("1001", "Alice", "A", None)


@pytest.mark.unit
def test_parse_csv_headerless_two_columns():
    data = b"1001,Alice\n1002,Bob\n"
    entries = parse_students(data, "roster.csv")
    assert entries[0][0] == "1001"
    assert entries[0][1] == "Alice"


@pytest.mark.unit
def test_duplicate_roll_in_file_raises():
    data = b"roll_no,name\n1001,Alice\n1001,Bob\n"
    with pytest.raises(StudentParseError, match="duplicate"):
        parse_students(data, "roster.csv")
