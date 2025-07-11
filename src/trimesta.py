import streamlit as st
import pandas as pd
import os
from app.data_loader import load_students
from app.state_manager import init_session_state_matrix
from app.data_visualization import (
    plot_grade_distribution,
    plot_grades_by_assignment,
    plot_student_progress, 
    plot_class_trimester_summary
)
from app.data_statistics import compute_student_weighted_average, compute_trimester_averages

# --- Class selection ---
st.sidebar.header("Class Selection")
xlsx_files = [f for f in os.listdir('data') if f.endswith('.xlsx')]
available_classes = sorted([f.replace('.xlsx', '') for f in xlsx_files])

if not available_classes:
    st.error("No class files found.")
    st.stop()

class_name = st.sidebar.selectbox("Choose a class", available_classes)
student_file = f"data/{class_name}.xlsx"
grades_file = f"data/grades_matrix_{class_name}.csv"

# --- Load students and initialize matrix ---
students_df = load_students(student_file)
init_session_state_matrix(grades_file, students_df, class_name)
grade_matrix = st.session_state["grade_matrix"]
meta_df = st.session_state["assignment_meta"]

# --- Show full class matrix (first) ---
st.title("Trimesta — Assignment Tracker")
st.subheader(f"Grade table for class {class_name}")
st.dataframe(grade_matrix)

# --- Assignment section ---
assignments = [col for col in grade_matrix.columns if col != "Full Name"]
selected_assignment = st.selectbox("Select or add an assignment", assignments + ["➕ New assignment"])

if selected_assignment == "➕ New assignment":
    new_name = st.text_input("Enter new assignment name")
    new_coeff = st.number_input("Coefficient (weight)", min_value=0.1, max_value=10.0, step=0.1, value=1.0)
    new_trimester = st.selectbox("Trimester", ["T1", "T2", "T3"])
    confirm = st.button("Create assignment")

    if confirm and new_name and new_name not in grade_matrix.columns:
        grade_matrix[new_name] = pd.NA
        selected_assignment = new_name
        st.success(f"Assignment '{new_name}' added.")

        meta_file = f"data/assignments_meta_{class_name}.csv"
        new_meta = pd.DataFrame([{"Assignment": new_name, "Coefficient": new_coeff, "Trimester": new_trimester}])
        if os.path.exists(meta_file):
            meta_df = pd.read_csv(meta_file)
            meta_df = pd.concat([meta_df, new_meta], ignore_index=True)
        else:
            meta_df = new_meta
        meta_df.to_csv(meta_file, index=False)
        st.session_state["assignment_meta"] = meta_df

# --- Grade input for multiple students ---
st.subheader(f"Assign grade for: {selected_assignment}")

# Reset input fields on rerun if flag is set
if st.session_state.get("reset_inputs", False):
    st.session_state["grade_input"] = ""
    st.session_state["student_selector"] = []
    st.session_state["reset_inputs"] = False  # Clear the flag

selected_students = st.multiselect("Select students", students_df["Full Name"].tolist(), key="student_selector")
grade_input = st.text_input("Grade (e.g., 4.5)", key="grade_input")

if st.button("Assign Grade"):
    try:
        grade = float(grade_input.replace(",", "."))
        if 0 <= grade <= 6:
            for student in selected_students:
                grade_matrix.loc[grade_matrix["Full Name"] == student, selected_assignment] = grade
            st.success(f"Assigned grade {grade} to {len(selected_students)} student(s) for {selected_assignment}.")
            st.session_state["last_assignment_edit"] = {
                "assignment": selected_assignment,
                "students": selected_students,
                "grade": grade
            }
            grade_matrix.to_csv(grades_file, index=False)
            st.session_state["grade_input_placeholder"] = ""  # Reset input
            st.rerun()
        else:
            st.error("Grade must be between 0 and 6.")
    except ValueError:
        st.error("Invalid grade format.")

# --- Undo last entry ---
if "last_assignment_edit" in st.session_state:
    with st.expander("Undo last assigned grade"):
        last = st.session_state["last_assignment_edit"]
        st.write(f'Last: grade {last["grade"]} for assignment "{last["assignment"]}" to {len(last["students"])} student(s)')
        if st.button("Undo Last Assignment Grade"):
            for student in last["students"]:
                grade_matrix.loc[grade_matrix["Full Name"] == student, last["assignment"]] = pd.NA
            grade_matrix.to_csv(grades_file, index=False)
            del st.session_state["last_assignment_edit"]
            st.success("Last assigned grade has been removed.")
            st.experimental_rerun()

# --- Individual student view ---
with st.expander("Individual student analysis"):
    student_name = st.selectbox("Pick a student", grade_matrix["Full Name"].tolist(), key="student_name_selectbox")
    student_row = grade_matrix[grade_matrix["Full Name"] == student_name]

    if not student_row.empty:
        st.write("Grades for assignments:")
        st.dataframe(student_row.T.rename(columns={student_row.index[0]: student_name}))

        avg = compute_student_weighted_average(grade_matrix, meta_df, student_name)
        if avg is not None:
            st.markdown(f"**Weighted average (all trimesters):** {avg:.2f}")
            st.markdown(f"**Rounded weighted average (all trimesters):** {round(avg, 1)}")


        if st.checkbox("Show grade progression"):
            plot_student_progress(grade_matrix, student_name)

# --- Trimester summaries ---
st.markdown("---")
st.subheader("Trimester summaries")
avg_table = compute_trimester_averages(grade_matrix, meta_df)
st.dataframe(avg_table)

# --- Visualizations ---
st.markdown("---")
st.subheader("Class visualizations")

if st.checkbox("Show grade distribution histogram"):
    plot_grade_distribution(grade_matrix, title=f"Grade Distribution — Class {class_name}")

if st.checkbox("Show boxplot of grades by assignment"):
    plot_grades_by_assignment(grade_matrix)

if st.checkbox('Show class average per assignment by trimester'):
    plot_class_trimester_summary(grade_matrix, meta_df)

if st.checkbox("Show a student's grade progression"):
    name = st.selectbox("Select student", grade_matrix["Full Name"].tolist(), key="progress_name")
    plot_student_progress(grade_matrix, name)