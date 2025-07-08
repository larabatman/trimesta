import os
import pandas as pd
import streamlit as st

def init_session_state_matrix(grades_path: str, students_df: pd.DataFrame, class_name: str):
    if st.session_state.get("current_class") != class_name or "grade_matrix" not in st.session_state:
        # Grade matrix (load or initialize)
        try:
            df = pd.read_csv(grades_path)
        except FileNotFoundError:
            df = students_df[["Full Name"]].copy()
        st.session_state["grade_matrix"] = df
        st.session_state["grades_file"] = grades_path

        # Load metadata
        meta_file = f"data/assignments_meta_{class_name}.csv"
        if os.path.exists(meta_file):
            meta_df = pd.read_csv(meta_file)
        else:
            meta_df = pd.DataFrame(columns=["Assignment", "Coefficient", "Trimester"])
        st.session_state["assignment_meta"] = meta_df  # ✅ This line is required!

        # Track current class to reload on change
        st.session_state["current_class"] = class_name
