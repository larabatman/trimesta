import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_class_trimester_summary(grade_matrix: pd.DataFrame, meta_df: pd.DataFrame):
    """
    Plots the average grade per assignment grouped by trimester.
    Only includes assignments that exist in both the grade matrix and metadata.
    """
    meta = meta_df.copy()
    meta = meta[meta["Assignment"].isin(grade_matrix.columns)]  # only keep assignments that exist

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"T1": "#8ecae6", "T2": "#ffb703", "T3": "#90be6d"}

    plotted_any = False

    for trimester in ["T1", "T2", "T3"]:
        trimester_assignments = meta[meta["Trimester"] == trimester]["Assignment"]
        if not trimester_assignments.empty:
            means = grade_matrix[trimester_assignments].mean(skipna=True)
            ax.plot(
                means.index,
                means.values,
                marker="o",
                label=f"{trimester} average",
                color=colors[trimester],
                linewidth=2,
            )
            plotted_any = True

    if not plotted_any:
        st.info("No trimester-tagged assignments available for class summary.")
        return

    ax.set_title("Class average per assignment by trimester")
    ax.set_ylabel("Grade")
    ax.set_ylim(0, 6.5)
    ax.set_xticks(range(len(means.index)))
    ax.set_xticklabels(means.index, rotation=45, ha="right")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    st.pyplot(fig)


def plot_grade_distribution(grade_matrix: pd.DataFrame, title="Grade Distribution"):
    melted = grade_matrix.drop(columns=["Full Name"]).melt(value_name="Grade").dropna()
    fig, ax = plt.subplots()
    sns.histplot(melted["Grade"], bins=10, kde=True, ax=ax)
    ax.set_title(title)
    st.pyplot(fig)

def plot_grades_by_assignment(grade_matrix: pd.DataFrame):
    melted = grade_matrix.drop(columns=["Full Name"]).melt(var_name="Assignment", value_name="Grade").dropna()
    fig, ax = plt.subplots()
    sns.boxplot(x="Assignment", y="Grade", data=melted, ax=ax)
    ax.set_title("Grade Distribution by Assignment")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
    st.pyplot(fig)

def plot_student_progress(grade_matrix: pd.DataFrame, student_name: str):
    row = grade_matrix[grade_matrix["Full Name"] == student_name]
    if row.empty:
        st.warning("Student not found.")
        return

    series = row.drop(columns=["Full Name"]).T.dropna().squeeze()
    fig, ax = plt.subplots()
    ax.plot(series.index, series.values, marker="o")
    ax.set_title(f"Progress of {student_name}")
    ax.set_ylabel("Grade")
    ax.set_xlabel("Assignment")
    ax.set_ylim(0, 6)
    ax.grid(True)
    st.pyplot(fig)
