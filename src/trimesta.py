import streamlit as st
import pandas as pd
from app.data_loader import load_students, save_grades
from app.state_manager import init_session_state
from app.data_statistics import compute_weighted_average
from app.ui_components import grade_entry_form

# Load students from Excel
students_df = load_students('data/901.xlsx')

# Initialize session state (grades_df, etc.)
init_session_state()
grades_df = st.session_state["grades_df"]

# Title
st.title('Trimesta')

# Sort and display student list
student_names = sorted(students_df['Full Name'].tolist())
selected_name = st.selectbox("Choose a student", student_names, placeholder='Start typing a name...')

# Initialize and clear form inputs if student changes
if "last_selected_student" not in st.session_state:
    st.session_state["last_selected_student"] = None

if st.session_state["last_selected_student"] != selected_name:
    st.session_state["grade_input"] = ""
    st.session_state["coeff_input"] = "1.0"
    st.session_state["trimester_input"] = "T1"
    st.session_state["last_selected_student"] = selected_name

# Show selected student
if selected_name:
    st.success(f'Selected: {selected_name}')

    # Get student ID safely
    selected_row = students_df[students_df["Full Name"] == selected_name]
    if selected_row.empty:
        st.error("Could not find the selected student.")
        st.stop()

    try:
        student_id = int(selected_row["ID"].iloc[0])
    except (KeyError, IndexError):
        st.error("Student ID not found in the table.")
        st.stop()

    # Grade entry form
    grade, coeff, trimester, submitted = grade_entry_form()

    if submitted and grade is not None and coeff is not None:
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

        # Auto-save to CSV
        save_grades(st.session_state['grades_df'], "data/grades_901.csv")

        st.success(f'Grade added: {grade} (Coeff: {coeff}) for {selected_name} in {trimester} and saved.')

    # Show current grades for this student
    grades_df = st.session_state['grades_df']
    if 'Full Name' in grades_df.columns and not grades_df.empty:
        student_grades = grades_df[grades_df['Full Name'] == selected_name]
    else:
        student_grades = pd.DataFrame(columns=grades_df.columns)

    if not student_grades.empty:
        st.subheader('Grades for this student:')
        st.dataframe(student_grades)

        average = compute_weighted_average(student_grades)
        if average is not None:
            st.markdown(f'**Weighted Average:** {average}')
        else:
            st.warning('No valid grades to compute average.')
