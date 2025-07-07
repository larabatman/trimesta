# app/ui_components.py

import streamlit as st

def grade_entry_form():
    """
    Renders a form to input a grade, coefficient, and trimester.
    Returns: (grade: float | None, coeff: float | None, trimester: str | None, submitted: bool)
    """
    with st.form('grade_entry'):
        grade_input = st.text_input('Enter grade', key='grade_input')
        coeff_input = st.text_input('Coefficient (default = 1.0)', value="1.0", key='coeff_input')
        trimester = st.selectbox('Trimester', ['T1', 'T2', 'T3'], key='trimester_input')
        submit = st.form_submit_button('Add Grade')

    if not submit:
        return None, None, None, False

    try:
        grade = round(float(grade_input.replace(',', '.')), 1)
        coeff = round(float(coeff_input.replace(',', '.')), 1)
        return grade, coeff, trimester, True
    except ValueError:
        st.error('Invalid number format. Please enter a valid grade and coefficient.')
        return None, None, None, False
