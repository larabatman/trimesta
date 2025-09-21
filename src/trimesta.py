import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app.data_loader import load_students
from app.state_manager import init_session_state_matrix
from app.data_visualization import (
    plot_grade_distribution,
    plot_grades_by_assignment,
    plot_student_progress,
    plot_class_trimester_summary,
)
from app.data_statistics import (
    compute_student_weighted_average,
    compute_trimester_averages,
)

# =======================
# Paramètres généraux
# =======================
# Dossier des données (configurable via variable d'env)
DATA_DIR = os.getenv("TRIMESTA_DATA_DIR", "data")


# =======================
# Sélection de la classe
# =======================
# On liste les fichiers Excel .xlsx ET .xls (en ignorant les fichiers temporaires ~$.)
excel_paths = []
for pattern in ("*.xlsx", "*.xls"):
    excel_paths.extend(p for p in Path(DATA_DIR).glob(pattern) if not p.name.startswith("~$"))
excel_paths = sorted(excel_paths)

if not excel_paths:
    st.error(f"Aucun fichier .xls/.xlsx trouvé dans « {DATA_DIR} ».")
    st.stop()

# On affiche un libellé explicite (nom + extension) pour éviter toute ambiguïté
options = [f"{p.stem} ({p.suffix.lower()})" for p in excel_paths]
selection = st.sidebar.selectbox("Choisir un fichier de classe", options)

# Résolution du chemin sélectionné
selected_idx = options.index(selection)
student_file = excel_paths[selected_idx]                 # chemin complet du fichier Excel
class_name = student_file.stem                           # ex. "901"
grades_file = Path(DATA_DIR) / f"grades_matrix_{class_name}.csv"
meta_file = Path(DATA_DIR) / f"assignments_meta_{class_name}.csv"

# Chargement des élèves (load_students gère .xls/.xlsx + FR/EN + anonymisation du nom)
try:
    students_df = load_students(str(student_file))
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier élèves : {student_file}")
    st.exception(e)
    st.stop()

# Initialisation de l'état de session pour cette classe (matrice + métadonnées)
init_session_state_matrix(str(grades_file), students_df, class_name)
grade_matrix = st.session_state["grade_matrix"]
meta_df = st.session_state["assignment_meta"]


# ======================================
# Tableau complet de la classe (en premier)
# ======================================
st.title("Trimesta — Suivi des évaluations")
st.subheader(f"Tableau des notes — Classe {class_name}")
st.dataframe(grade_matrix)


# ==========================
# Section : Évaluations
# ==========================
# Liste des évaluations existantes (toutes les colonnes sauf « Full Name »)
assignments = [col for col in grade_matrix.columns if col != "Full Name"]
selected_assignment = st.selectbox(
    "Sélectionner ou ajouter une évaluation",
    assignments + ["➕ Nouvelle évaluation"],
)

# Création d’une nouvelle évaluation
if selected_assignment == "➕ Nouvelle évaluation":
    new_name = st.text_input("Nom de la nouvelle évaluation")
    new_coeff = st.number_input("Coefficient (pondération)", min_value=0.1, max_value=10.0, step=0.1, value=1.0)
    new_trimester = st.selectbox("Trimestre", ["T1", "T2", "T3"])
    confirm = st.button("Créer l’évaluation")

    if confirm:
        if not new_name:
            st.warning("Veuillez saisir un nom d’évaluation.")
        elif new_name in grade_matrix.columns:
            st.warning("Cette évaluation existe déjà.")
        else:
            # Ajout de la colonne dans la matrice (valeurs manquantes par défaut)
            grade_matrix[new_name] = pd.NA
            # Mise à jour du fichier méta et de l'état de session
            new_meta = pd.DataFrame([{"Assignment": new_name, "Coefficient": new_coeff, "Trimester": new_trimester}])
            if meta_file.exists():
                meta_df = pd.read_csv(meta_file)
                meta_df = pd.concat([meta_df, new_meta], ignore_index=True)
            else:
                meta_df = new_meta
            meta_df.to_csv(meta_file, index=False)
            st.session_state["assignment_meta"] = meta_df
            # Sauvegarder la matrice mise à jour
            grade_matrix.to_csv(grades_file, index=False)
            st.success(f"Évaluation « {new_name} » ajoutée.")
            # Forcer un rafraîchissement pour que la nouvelle évaluation apparaisse dans la liste
            st.rerun()


# ===========================================
# Saisie de note pour plusieurs élèves
# ===========================================
# Remise à zéro des champs si un précédent ajout a demandé un reset
if st.session_state.get("reset_inputs", False):
    st.session_state["grade_input"] = ""
    st.session_state["student_selector"] = []
    st.session_state["reset_inputs"] = False

# Si aucune évaluation n’existe encore, on n’affiche pas le formulaire de saisie
assignments = [col for col in grade_matrix.columns if col != "Full Name"]
if not assignments or selected_assignment == "➕ Nouvelle évaluation":
    st.info("Créez d’abord une évaluation pour pouvoir attribuer des notes.")
else:
    st.subheader(f"Attribuer une note pour : {selected_assignment}")

    selected_students = st.multiselect(
        "Sélectionner des élèves",
        students_df["Full Name"].tolist(),
        key="student_selector",
    )
    grade_input = st.text_input("Note (ex. 4,5)", key="grade_input")

    if st.button("Attribuer la note"):
        try:
            grade = float(grade_input.replace(",", "."))
            if 0 <= grade <= 6:
                # Affectation de la note à chaque élève sélectionné
                for student in selected_students:
                    grade_matrix.loc[grade_matrix["Full Name"] == student, selected_assignment] = grade

                # Mémoriser la dernière action pour l'undo
                st.session_state["last_assignment_edit"] = {
                    "assignment": selected_assignment,
                    "students": selected_students,
                    "grade": grade,
                }

                # Sauvegarde
                grade_matrix.to_csv(grades_file, index=False)
                st.success(
                    f"Note {grade} attribuée à {len(selected_students)} élève(s) "
                    f"pour « {selected_assignment} »."
                )

                # Demande de remise à zéro des champs, puis rerun
                st.session_state["reset_inputs"] = True
                st.rerun()
            else:
                st.error("La note doit être comprise entre 0 et 6.")
        except ValueError:
            st.error("Format de note invalide.")


# ==============================
# Annuler la dernière attribution
# ==============================
if "last_assignment_edit" in st.session_state:
    with st.expander("Annuler la dernière attribution"):
        last = st.session_state["last_assignment_edit"]
        st.write(
            f"Dernière action : note {last['grade']} pour l’évaluation « {last['assignment']} » "
            f"attribuée à {len(last['students'])} élève(s)."
        )
        if st.button("Annuler cette attribution"):
            for student in last["students"]:
                grade_matrix.loc[grade_matrix["Full Name"] == student, last["assignment"]] = pd.NA
            grade_matrix.to_csv(grades_file, index=False)
            del st.session_state["last_assignment_edit"]
            st.success("La dernière attribution a été annulée.")
            st.rerun()


# =====================
# Analyse par élève
# =====================
with st.expander("Analyse par élève"):
    if grade_matrix.empty:
        st.info("Aucune donnée à afficher.")
    else:
        student_name = st.selectbox(
            "Choisir un élève",
            grade_matrix["Full Name"].tolist(),
            key="student_name_selectbox",
        )
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


# ==========================
# Synthèses par trimestre
# ==========================
st.markdown("---")
st.subheader("Synthèses par trimestre")
avg_table = compute_trimester_averages(grade_matrix, meta_df)
st.dataframe(avg_table)


# ==========================
# Visualisations de la classe
# ==========================
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