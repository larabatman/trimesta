# src/app/data_statistics.py
import pandas as pd

# ---------- Helpers ----------
def _normalize_name_column(df: pd.DataFrame) -> str:
    for c in ["Full Name", "Nom complet", "Nom Complet", "Nom"]:
        if c in df.columns:
            return c
    return "Full Name"

def _normalize_meta_columns(meta_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize meta columns to: Assignment, Coefficient, Trimester (accept FR/EN)."""
    if meta_df is None or meta_df.empty:
        return pd.DataFrame(columns=["Assignment", "Coefficient", "Trimester"])
    mapping = {}
    lower_map = {str(c).strip().lower(): c for c in meta_df.columns}

    def _pick(src_names, target):
        for s in src_names:
            key = s.lower()
            if key in lower_map:
                mapping[lower_map[key]] = target
                return

    _pick(["Assignment", "Évaluation", "Evaluation"], "Assignment")
    _pick(["Coefficient", "Pondération", "Ponderation"], "Coefficient")
    _pick(["Trimester", "Trimestre"], "Trimester")

    meta = meta_df.rename(columns=mapping).copy()
    for col in ["Assignment", "Coefficient", "Trimester"]:
        if col not in meta.columns:
            meta[col] = pd.Series(dtype="object")
    return meta[["Assignment", "Coefficient", "Trimester"]]

# ---------- Public API ----------
def compute_student_weighted_average(
    grade_matrix: pd.DataFrame,
    meta_df: pd.DataFrame,
    student_name: str
):
    """
    Weighted average for a single student. Falls back to weight=1.0 when meta is missing.
    Returns float rounded to 2 decimals, or None if not computable.
    """
    if grade_matrix is None or grade_matrix.empty:
        return None

    name_col = _normalize_name_column(grade_matrix)
    if name_col not in grade_matrix.columns:
        return None

    row = grade_matrix[grade_matrix[name_col] == student_name]
    if row.empty:
        return None

    assignment_cols = [c for c in grade_matrix.columns if c != name_col]
    if not assignment_cols:
        return None

    grades = pd.to_numeric(row.iloc[0][assignment_cols], errors="coerce").dropna()
    if grades.empty:
        return None

    meta = _normalize_meta_columns(meta_df).set_index("Assignment")
    # default weights = 1.0
    weights = pd.Series(1.0, index=grades.index)
    if not meta.empty:
        w = pd.to_numeric(meta.reindex(grades.index)["Coefficient"], errors="coerce")
        weights = w.fillna(1.0)

    mask = grades.notna() & weights.notna()
    grades = grades[mask]
    weights = weights[mask]
    if grades.empty or weights.sum() == 0:
        return None

    avg = (grades * weights).sum() / weights.sum()
    return round(float(avg), 2)

def compute_trimester_averages(
    grade_matrix: pd.DataFrame,
    meta_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Per-student weighted averages by trimester plus global.
    Returns DataFrame with columns: ['Full Name','T1','T2','T3','Global'].
    """
    empty_out = pd.DataFrame(columns=["Full Name", "T1", "T2", "T3", "Global"])

    if grade_matrix is None or grade_matrix.empty:
        return empty_out

    name_col = _normalize_name_column(grade_matrix)
    if name_col not in grade_matrix.columns:
        return empty_out

    result = {"Full Name": grade_matrix[name_col].tolist()}
    student_count = len(grade_matrix)

    meta = _normalize_meta_columns(meta_df).copy()
    # keep only assignments that exist in the matrix
    existing_assignments = [c for c in grade_matrix.columns if c != name_col]
    meta = meta[meta["Assignment"].isin(existing_assignments)]

    # By trimester
    for trimester in ["T1", "T2", "T3"]:
        trimester_assignments = meta[meta["Trimester"] == trimester]["Assignment"].tolist()
        if not trimester_assignments:
            result[trimester] = [None] * student_count
            continue

        coefs = (
            pd.to_numeric(
                meta.set_index("Assignment").loc[trimester_assignments]["Coefficient"],
                errors="coerce",
            ).fillna(1.0)
        )

        values_list = []
        for _, row in grade_matrix.iterrows():
            grades = pd.to_numeric(row.reindex(trimester_assignments), errors="coerce")
            valid = grades.notna()
            vals = grades[valid]
            wts = coefs[valid]
            if vals.empty or wts.sum() == 0:
                values_list.append(None)
            else:
                avg = (vals * wts).sum() / wts.sum()
                values_list.append(round(float(avg), 2))
        result[trimester] = values_list

    # Global over all available assignments
    all_assignments = meta["Assignment"].tolist()
    if all_assignments:
        coefs_all = pd.to_numeric(
            meta.set_index("Assignment")["Coefficient"], errors="coerce"
        ).fillna(1.0)

        global_list = []
        for _, row in grade_matrix.iterrows():
            grades = pd.to_numeric(row.reindex(all_assignments), errors="coerce")
            valid = grades.notna()
            vals = grades[valid]
            wts = coefs_all[valid]
            if vals.empty or wts.sum() == 0:
                global_list.append(None)
            else:
                avg = (vals * wts).sum() / wts.sum()
                global_list.append(round(float(avg), 2))
    else:
        global_list = [None] * student_count

    result["Global"] = global_list
    return pd.DataFrame(result, columns=["Full Name", "T1", "T2", "T3", "Global"])
