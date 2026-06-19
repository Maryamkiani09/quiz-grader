"""
Unit tests for the Automated Quiz Grading System.
Run with: python -m pytest tests/test_grader.py -v
"""

import os
import sys
import csv
import tempfile
import pytest

# Allow imports from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from grader import (
    load_answer_key,
    load_student_answers,
    grade_student,
    assign_grade,
    compute_analytics,
)


# ──────────────────────────────────────────────
#  FIXTURES
# ──────────────────────────────────────────────

@pytest.fixture
def tmp_csv(tmp_path):
    """Helper to create a temp CSV file from rows."""
    def _make(filename, rows):
        path = tmp_path / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
        return str(path)
    return _make


@pytest.fixture
def sample_key(tmp_csv):
    return tmp_csv("key.csv", [
        ["question_number", "correct_answer", "marks"],
        [1, "A", 2],
        [2, "C", 1],
        [3, "B", 2],
    ])


@pytest.fixture
def sample_students(tmp_csv):
    return tmp_csv("students.csv", [
        ["student_id", "name", "q1", "q2", "q3"],
        ["S001", "Alice", "A", "C", "B"],   # perfect
        ["S002", "Bob",   "B", "C", "B"],   # q1 wrong
        ["S003", "Carol", "B", "A", "A"],   # all wrong
    ])


# ──────────────────────────────────────────────
#  LOADING TESTS
# ──────────────────────────────────────────────

def test_load_answer_key(sample_key):
    key = load_answer_key(sample_key)
    assert len(key) == 3
    assert key[1] == {"answer": "A", "marks": 2}
    assert key[2] == {"answer": "C", "marks": 1}


def test_load_answer_key_missing_file():
    with pytest.raises(FileNotFoundError):
        load_answer_key("nonexistent.csv")


def test_load_student_answers(sample_students):
    students = load_student_answers(sample_students)
    assert len(students) == 3
    assert students[0]["name"] == "Alice"
    assert students[0]["answers"][1] == "A"


# ──────────────────────────────────────────────
#  GRADING TESTS
# ──────────────────────────────────────────────

@pytest.fixture
def answer_key():
    return {1: {"answer": "A", "marks": 2}, 2: {"answer": "C", "marks": 1}, 3: {"answer": "B", "marks": 2}}


def test_perfect_score(answer_key):
    student = {"student_id": "S001", "name": "Alice", "answers": {1: "A", 2: "C", 3: "B"}}
    result = grade_student(student, answer_key)
    assert result["obtained"] == 5
    assert result["total"] == 5
    assert result["percentage"] == 100.0
    assert result["grade"] == "A+"


def test_zero_score(answer_key):
    student = {"student_id": "S002", "name": "Bob", "answers": {1: "B", 2: "A", 3: "C"}}
    result = grade_student(student, answer_key)
    assert result["obtained"] == 0
    assert result["percentage"] == 0.0
    assert result["grade"] == "F"


def test_partial_score(answer_key):
    student = {"student_id": "S003", "name": "Carol", "answers": {1: "A", 2: "A", 3: "B"}}
    result = grade_student(student, answer_key)
    assert result["obtained"] == 4   # q1=2, q3=2
    assert result["percentage"] == 80.0
    assert result["grade"] == "A"


def test_missing_answer_treated_as_wrong(answer_key):
    student = {"student_id": "S004", "name": "Dave", "answers": {}}
    result = grade_student(student, answer_key)
    assert result["obtained"] == 0


# ──────────────────────────────────────────────
#  GRADE BOUNDARY TESTS
# ──────────────────────────────────────────────

@pytest.mark.parametrize("pct, expected", [
    (95, "A+"), (90, "A+"),
    (85, "A"),  (80, "A"),
    (75, "B"),  (70, "B"),
    (65, "C"),  (60, "C"),
    (55, "D"),  (50, "D"),
    (49, "F"),  (0,  "F"),
])
def test_grade_boundaries(pct, expected):
    assert assign_grade(pct) == expected


# ──────────────────────────────────────────────
#  ANALYTICS TESTS
# ──────────────────────────────────────────────

def test_analytics(answer_key):
    students = [
        {"student_id": "S001", "name": "Alice", "answers": {1: "A", 2: "C", 3: "B"}},  # 100%
        {"student_id": "S002", "name": "Bob",   "answers": {1: "B", 2: "A", 3: "C"}},  # 0%
    ]
    from grader import grade_all
    results = grade_all(students, answer_key)
    analytics = compute_analytics(results, answer_key)

    assert analytics["class_size"] == 2
    assert analytics["highest"] == 5
    assert analytics["lowest"] == 0
    assert analytics["average"] == 50.0
    assert analytics["pass_count"] == 1
    assert analytics["fail_count"] == 1


def test_question_difficulty(answer_key):
    students = [
        {"student_id": "S001", "name": "Alice", "answers": {1: "A", 2: "C", 3: "B"}},
        {"student_id": "S002", "name": "Bob",   "answers": {1: "A", 2: "A", 3: "C"}},
    ]
    from grader import grade_all
    results = grade_all(students, answer_key)
    analytics = compute_analytics(results, answer_key)
    diff = analytics["question_difficulty"]

    # Q1: both got it right → 100% → Easy
    assert diff[1]["success_rate"] == 100.0
    assert diff[1]["difficulty"] == "Easy"

    # Q3: only Bob got it wrong → 50% → Medium
    assert diff[3]["success_rate"] == 50.0
    assert diff[3]["difficulty"] == "Medium"
