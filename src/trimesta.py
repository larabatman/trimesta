import streamlit as st
import pandas as pd
import os
from app.data_loader import load_students, save_grades
from app.state_manager import init_session_state
from app.data_statistics import compute_weighted_average
from app.ui_components import grade_entry_form
from app.data_visualization import (
    plot_grade_distribution,
    plot_grades_by_trimester,
    plot_student_progress
)

# -------------------------------
# Sidebar: Class selection
# -------------------------------
st.sidebar.header('Class Selection')

# Get all .xlsx files in /data folder (student files)
xlsx_files = [f for f in os.listdir('data') if f.endswith('.xlsx')]
available_classes = sorted([f.replace('.xlsx', '') for f in xlsx_files])

if not available_classes:
    st.error("No class files found in /data.")
    st.stop()

class_name = st.sidebar.selectbox("Choose a class", available_classes)
student_file = f'data/{class_name}.xlsx'
grades_file = f'data/grades_{class_name}.csv'

# -------------------------------
# Load data and initialize session state
# -------------------------------
students_df = load_students(student_file)
init_session_state(grades_path=grades_file)
grades_df = st.session_state["grades_df"]

# -------------------------------
# Title and student selection
# -------------------------------
st.title('Trimesta')

student_names = sorted(students_df['Full Name'].tolist())
selected_name = st.selectbox("Choose a student", student_names, placeholder='Start typing a name...')

# Reset form inputs when switching students
if "last_selected_student" not in st.session_state:
    st.session_state["last_selected_student"] = None

if st.session_state["last_selected_student"] != selected_name:
    st.session_state["grade_input"] = ""
    st.session_state["coeff_input"] = "1.0"
    st.session_state["trimester_input"] = "T1"
    st.session_state["last_selected_student"] = selected_name

# -------------------------------
# Grade entry and processing
# -------------------------------
if selected_name:
    st.success(f'Selected: {selected_name}')

    selected_row = students_df[students_df["Full Name"] == selected_name]
    if selected_row.empty:
        st.error("Could not find the selected student.")
        st.stop()

    try:
        student_id = int(selected_row["ID"].iloc[0])
    except (KeyError, IndexError):
        st.error("Student ID not found.")
        st.stop()

    grade, coeff, trimester, submitted = grade_entry_form()

    if submitted and grade is not None and coeff is not None:
        previous_grades = grades_df[grades_df["Full Name"] == selected_name]
        previous_avg = compute_weighted_average(previous_grades)

        new_row = {
            'ID': student_id,
            'Full Name': selected_name,
            'Grade': grade,
            'Coefficient': coeff,
            'Trimester': trimester
        }

        st.session_state['grades_df'] = pd.concat(
            [grades_df, pd.DataFrame([new_row])],
            ignore_index=True
        )

        save_grades(st.session_state['grades_df'], grades_file)
        st.success(f'Grade added: {grade} (Coeff: {coeff}) for {selected_name} in {trimester} and saved.')

        if previous_avg is not None:
            delta = round(grade - previous_avg, 2)
            if delta > 0:
                st.info(f"This grade is {delta} points above the previous average ({previous_avg}).")
            elif delta < 0:
                st.info(f"This grade is {abs(delta)} points below the previous average ({previous_avg}).")
            else:
                st.info("This grade matches the previous average.")

# -------------------------------
# Student's grade view and plot
# -------------------------------
    grades_df = st.session_state['grades_df']
    student_grades = grades_df[grades_df['Full Name'] == selected_name] if 'Full Name' in grades_df.columns else pd.DataFrame()

    if not student_grades.empty:
        st.subheader('Grades for this student:')
        st.dataframe(student_grades)

        average = compute_weighted_average(student_grades)
        if average is not None:
            st.markdown(f'**Weighted Average:** {average}')
        else:
            st.warning('No valid grades to compute average.')

        if st.checkbox("Show student's grade progression (line plot)"):
            plot_student_progress(grades_df, selected_name)

# -------------------------------
# Class-wide visualizations
# -------------------------------
st.markdown('---')
st.subheader('Class visualizations')

if st.checkbox('Show grade distribution histogram'):
    plot_grade_distribution(grades_df, title=f'Grade Distribution — Class {class_name}')

if st.checkbox('Show boxplot of grades by trimester'):
    st.caption(f"Showing data for class: {class_name}")
    plot_grades_by_trimester(grades_df)
