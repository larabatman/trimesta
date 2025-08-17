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

# --- Sélection de la classe ---
st.sidebar.header("Sélection de la classe")
xlsx_files = [f for f in os.listdir('data') if f.endswith('.xlsx')]
available_classes = sorted([f.replace('.xlsx', '') for f in xlsx_files])

if not available_classes:
    st.error("Aucun fichier de classe trouvé.")
    st.stop()

class_name = st.sidebar.selectbox("Choisir une classe", available_classes)
student_file = f"data/{class_name}.xlsx"
grades_file = f"data/grades_matrix_{class_name}.csv"

# --- Charger les élèves et initialiser la matrice ---
students_df = load_students(student_file)
init_session_state_matrix(grades_file, students_df, class_name)
grade_matrix = st.session_state["grade_matrix"]
meta_df = st.session_state["assignment_meta"]

# --- Tableau complet de la classe (en premier) ---
st.title("Trimesta — Suivi des évaluations")
st.subheader(f"Tableau des notes — Classe {class_name}")
st.dataframe(grade_matrix)

# --- Section Évaluations ---
assignments = [col for col in grade_matrix.columns if col != "Full Name"]
selected_assignment = st.selectbox("Sélectionner ou ajouter une évaluation", assignments + ["➕ Nouvelle évaluation"])

if selected_assignment == "➕ Nouvelle évaluation":
    new_name = st.text_input("Nom de la nouvelle évaluation")
    new_coeff = st.number_input("Coefficient (pondération)", min_value=0.1, max_value=10.0, step=0.1, value=1.0)
    new_trimester = st.selectbox("Trimestre", ["T1", "T2", "T3"])
    confirm = st.button("Créer l’évaluation")

    if confirm and new_name and new_name not in grade_matrix.columns:
        grade_matrix[new_name] = pd.NA
        selected_assignment = new_name
        st.success(f"Évaluation « {new_name} » ajoutée.")

        meta_file = f"data/assignments_meta_{class_name}.csv"
        new_meta = pd.DataFrame([{"Assignment": new_name, "Coefficient": new_coeff, "Trimester": new_trimester}])
        if os.path.exists(meta_file):
            meta_df = pd.read_csv(meta_file)
            meta_df = pd.concat([meta_df, new_meta], ignore_index=True)
        else:
            meta_df = new_meta
        meta_df.to_csv(meta_file, index=False)
        st.session_state["assignment_meta"] = meta_df

# --- Saisie de note pour plusieurs élèves ---
st.subheader(f"Attribuer une note pour : {selected_assignment}")

# Réinitialiser les champs si le drapeau est activé
if st.session_state.get("reset_inputs", False):
    st.session_state["grade_input"] = ""
    st.session_state["student_selector"] = []
    st.session_state["reset_inputs"] = False  # On retire le drapeau

selected_students = st.multiselect("Sélectionner des élèves", students_df["Full Name"].tolist(), key="student_selector")
grade_input = st.text_input("Note (ex. 4,5)", key="grade_input")

if st.button("Attribuer la note"):
    try:
        grade = float(grade_input.replace(",", "."))
        if 0 <= grade <= 6:
            for student in selected_students:
                grade_matrix.loc[grade_matrix["Full Name"] == student, selected_assignment] = grade
            st.success(f"Note {grade} attribuée à {len(selected_students)} élève(s) pour « {selected_assignment} ».")
            st.session_state["last_assignment_edit"] = {
                "assignment": selected_assignment,
                "students": selected_students,
                "grade": grade
            }
            grade_matrix.to_csv(grades_file, index=False)
            st.session_state["grade_input_placeholder"] = ""  # remise à zéro de l’affichage
            st.rerun()
        else:
            st.error("La note doit être comprise entre 0 et 6.")
    except ValueError:
        st.error("Format de note invalide.")

# --- Annuler la dernière saisie ---
if "last_assignment_edit" in st.session_state:
    with st.expander("Annuler la dernière attribution"):
        last = st.session_state["last_assignment_edit"]
        st.write(
            f"Dernière action : note {last['grade']} pour l’évaluation « {last['assignment']} » "
            f"à {len(last['students'])} élève(s)"
        )
        if st.button("Annuler cette attribution"):
            for student in last["students"]:
                grade_matrix.loc[grade_matrix["Full Name"] == student, last["assignment"]] = pd.NA
            grade_matrix.to_csv(grades_file, index=False)
            del st.session_state["last_assignment_edit"]
            st.success("La dernière attribution a été annulée.")
            st.experimental_rerun()

# --- Analyse par élève ---
with st.expander("Analyse par élève"):
    student_name = st.selectbox("Choisir un élève", grade_matrix["Full Name"].tolist(), key="student_name_selectbox")
    student_row = grade_matrix[grade_matrix["Full Name"] == student_name]

    if not student_row.empty:
        st.write("Notes par évaluation :")
        st.dataframe(student_row.T.rename(columns={student_row.index[0]: student_name}))

        avg = compute_student_weighted_average(grade_matrix, meta_df, student_name)
        if avg is not None:
            st.markdown(f"**Moyenne pondérée (tous trimestres) :** {avg:.2f}")
            st.markdown(f"**Moyenne pondérée arrondie (au dixième) :** {round(avg, 1)}")

        if st.checkbox("Afficher l’évolution des notes"):
            plot_student_progress(grade_matrix, student_name)

# --- Synthèses par trimestre ---
st.markdown("---")
st.subheader("Synthèses par trimestre")
avg_table = compute_trimester_averages(grade_matrix, meta_df)
st.dataframe(avg_table)

# --- Visualisations ---
st.markdown("---")
st.subheader("Visualisations de la classe")

if st.checkbox("Afficher l’histogramme des notes"):
    plot_grade_distribution(grade_matrix, title=f"Répartition des notes — Classe {class_name}")

if st.checkbox("Afficher le boxplot des notes par évaluation"):
    plot_grades_by_assignment(grade_matrix)

if st.checkbox("Afficher la moyenne de la classe par évaluation et par trimestre"):
    plot_class_trimester_summary(grade_matrix, meta_df)

if st.checkbox("Afficher l’évolution des notes d’un élève"):
    name = st.selectbox("Sélectionner un élève", grade_matrix["Full Name"].tolist(), key="progress_name")
    plot_student_progress(grade_matrix, name)
