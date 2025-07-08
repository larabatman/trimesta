import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
