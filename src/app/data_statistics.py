import pandas as pd

import pandas as pd

def compute_student_weighted_average(grade_matrix: pd.DataFrame, meta_df: pd.DataFrame, student_name: str):
    """
    Compute the weighted average for a single student using assignment coefficients from metadata.
    Returns a float or None if not computable.
    """
    if "Full Name" not in grade_matrix.columns:
        return None

    row = grade_matrix[grade_matrix["Full Name"] == student_name]
    if row.empty or row.shape[1] <= 1:
        return None

    # Drop the name column and extract grade series
    grades = row.drop(columns=["Full Name"]).squeeze()

    # Ensure we have a valid Series, not just pd.NA or a scalar
    if not isinstance(grades, pd.Series):
        return None

    # Get only assignments with numeric grades
    valid_assignments = grades.dropna().index.tolist()
    if not valid_assignments:
        return None

    # Match with metadata and extract weights
    meta = meta_df.set_index("Assignment").reindex(valid_assignments)
    weights = meta["Coefficient"].fillna(1.0)
    values = grades[valid_assignments].astype(float)

    if weights.sum() == 0 or values.empty:
        return None

    weighted_avg = (values * weights).sum() / weights.sum()
    return round(weighted_avg, 2)

def compute_trimester_averages(grade_matrix: pd.DataFrame, meta_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes weighted averages per student for each trimester.
    Returns a DataFrame like:
    | Full Name       | T1   | T2   | T3   | Global |
    """
    result = {"Full Name": grade_matrix["Full Name"]}
    student_names = grade_matrix["Full Name"].tolist()

    for trimester in ["T1", "T2", "T3"]:
        trimester_assignments = meta_df[meta_df["Trimester"] == trimester]["Assignment"].tolist()

        if not trimester_assignments:
            result[trimester] = [None] * len(student_names)
            continue

        coefs = meta_df.set_index("Assignment").loc[trimester_assignments]["Coefficient"].fillna(1.0)
        trimester_grades = grade_matrix[["Full Name"] + trimester_assignments].copy()

        trimester_averages = []
        for _, row in trimester_grades.iterrows():
            grades = row[trimester_assignments]
            weights = coefs[grades.notna()]
            values = grades.dropna().astype(float)
            if weights.sum() == 0 or values.empty:
                trimester_averages.append(None)
            else:
                avg = (values * weights).sum() / weights.sum()
                trimester_averages.append(round(avg, 2))
        result[trimester] = trimester_averages

    # Global average (using all available assignments)
    global_averages = []
    all_assignments = meta_df["Assignment"].tolist()
    coefs_all = meta_df.set_index("Assignment")["Coefficient"].fillna(1.0)
    for _, row in grade_matrix.iterrows():
        grades = row[all_assignments]
        weights = coefs_all[grades.notna()]
        values = grades.dropna().astype(float)
        if weights.sum() == 0 or values.empty:
            global_averages.append(None)
        else:
            avg = (values * weights).sum() / weights.sum()
            global_averages.append(round(avg, 2))
    result["Global"] = global_averages

    return pd.DataFrame(result)
