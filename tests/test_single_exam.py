# tests/test_single_exam.py

import os
import sys
import pandas as pd
import numpy as np
import pytest

# Make 'src' importable (so we can import app.* modules)
THIS_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from app.data_loader import load_students
from app.data_statistics import compute_student_weighted_average, compute_trimester_averages


def test_load_students_anonymizes_lastname(tmp_path):
    """
    Ensures load_students reads an Excel class list and builds 'Full Name',
    anonymizing last names by stripping vowels (keeping first letter).
    """
    df_in = pd.DataFrame({
        "Prénom": ["Camille", "Théo"],
        "Nom":    ["Duprez",  "Lévy"],
    })
    xlsx = tmp_path / "classe.xlsx"
    df_in.to_excel(xlsx, index=False)

    students = load_students(str(xlsx))  # defaults anonymize_last=True
    assert "Full Name" in students.columns
    assert "ID" in students.columns

    # Map first name -> anonymized last name
    name_map = {}
    for _, row in students.iterrows():
        full = row["Full Name"]
        parts = str(full).split()
        assert len(parts) >= 2
        first, last = parts[0], parts[-1]
        name_map[first] = last

    # "Duprez" -> keep D, remove u/e -> "Dprz"
    assert name_map["Camille"] == "Dprz"
    # "Lévy" -> keep L, remove é and y -> "Lv"
    assert name_map["Théo"] == "Lv"


def test_student_weighted_average_single_exam():
    """
    With a single exam, the weighted average for each student equals their grade,
    regardless of the coefficient value.
    """
    grade_matrix = pd.DataFrame({
        "Full Name": ["Camille Dprz", "Theo Lv", "Anais Brn"],
        "Examen 1":  [4.5, 6.0, 3.0],
    })
    meta_df = pd.DataFrame({
        "Assignment": ["Examen 1"],
        "Coefficient": [2.0],     # any positive weight is fine
        "Trimester":   ["T1"],
    })

    # Each student's weighted average equals their exam grade
    for student, expected in zip(grade_matrix["Full Name"], [4.5, 6.0, 3.0]):
        avg = compute_student_weighted_average(grade_matrix, meta_df, student)
        assert avg == pytest.approx(expected, rel=0, abs=1e-9)


def test_trimester_averages_and_class_mean_single_exam():
    """
    For a single exam mapped to T1, trimester T1 per-student averages equal their grades,
    T2/T3 are None, and the class mean for T1 matches the arithmetic mean.
    """
    grade_matrix = pd.DataFrame({
        "Full Name": ["Camille Dprz", "Theo Lv", "Anais Brn"],
        "Examen 1":  [4.5, 6.0, 3.0],
    })
    meta_df = pd.DataFrame({
        "Assignment": ["Examen 1"],
        "Coefficient": [1.0],
        "Trimester":   ["T1"],
    })

    avg_table = compute_trimester_averages(grade_matrix, meta_df)

    # Columns present and in order
    assert list(avg_table.columns) == ["Full Name", "T1", "T2", "T3", "Global"]

    # T1 equals original grades, Global equals the same (one exam)
    expected_T1 = [4.5, 6.0, 3.0]
    expected_Global = expected_T1

    assert avg_table["T1"].tolist() == expected_T1
    assert avg_table["Global"].tolist() == expected_Global

    # T2 and T3 are None for each student (no assignments there)
    assert all(v is None for v in avg_table["T2"].tolist())
    assert all(v is None for v in avg_table["T3"].tolist())

    # Class mean for T1
    class_mean = pd.to_numeric(avg_table["T1"]).mean()
    assert class_mean == pytest.approx((4.5 + 6.0 + 3.0) / 3.0, rel=0, abs=1e-12)


def test_logging_csv_roundtrip_single_exam(tmp_path):
    """
    Simulates data logging: save grade_matrix to CSV and read back,
    ensuring values are preserved.
    """
    grade_matrix = pd.DataFrame({
        "Full Name": ["Camille Dprz", "Theo Lv", "Anais Brn"],
        "Examen 1":  [4.5, 6.0, 3.0],
    })

    target = tmp_path / "grades_matrix_test.csv"
    grade_matrix.to_csv(target, index=False)

    loaded = pd.read_csv(target)
    # Same columns and shape
    assert list(loaded.columns) == list(grade_matrix.columns)
    assert loaded.shape == grade_matrix.shape

    # Values preserved (numeric column)
    pd.testing.assert_series_equal(
        pd.to_numeric(loaded["Examen 1"]),
        pd.Series([4.5, 6.0, 3.0], name="Examen 1"),
        check_names=True,
    )
