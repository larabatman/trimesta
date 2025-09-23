import os
from pathlib import Path
from datetime import datetime
import shutil
import json

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
# Fonctions utilitaires
# =======================
def _name_col(df: pd.DataFrame) -> str:
    """Find the 'full name' column across FR/EN variants."""
    for c in ["Full Name", "Nom complet", "Nom Complet", "Nom"]:
        if c in df.columns:
            return c
    # Fallback to 'Full Name' for downstream logic
    return "Full Name"

def sanitize_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make a copy that is Arrow-friendly:
    - ensure name column is string
    - coerce all other columns to numeric (NaN on errors)
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    name_col = _name_col(out)
    if name_col in out.columns:
        out[name_col] = out[name_col].astype(str)
    for col in out.columns:
        if col != name_col:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out

def make_backup(class_name, student_file, grades_file, meta_file, grade_matrix, meta_df, data_dir=DATA_DIR):
    """
    Crée un dossier d'instantané:
      data/backups/<classe>/<YYYYmmdd-HHMMSS>/
    avec:
      - grades_matrix_<classe>.csv (depuis la DataFrame si dispo, sinon copie du fichier)
      - assignments_meta_<classe>.csv (depuis la DataFrame si dispo, sinon copie du fichier)
      - le fichier Excel d'élèves (.xls/.xlsx) original
      - manifest.json
    Retourne le Path du dossier de sauvegarde.
    """
    data_dir = Path(data_dir)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = data_dir / "backups" / class_name / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Sauvegarde de la matrice de notes
    grades_path = backup_dir / f"grades_matrix_{class_name}.csv"
    if isinstance(grade_matrix, pd.DataFrame):
        grade_matrix.to_csv(grades_path, index=False)
    elif Path(grades_file).exists():
        shutil.copy2(grades_file, grades_path)

    # Sauvegarde des métadonnées d'évaluations
    meta_path = backup_dir / f"assignments_meta_{class_name}.csv"
    if isinstance(meta_df, pd.DataFrame):
        meta_df.to_csv(meta_path, index=False)
    elif Path(meta_file).exists():
        shutil.copy2(meta_file, meta_path)

    # Copie du fichier élèves (roster)
    sf = Path(student_file)
    if sf.exists():
        shutil.copy2(sf, backup_dir / sf.name)

    # Manifest
    manifest = {
        "class_name": class_name,
        "created_at": timestamp,
        "source_data_dir": str(Path(data_dir).resolve()),
        "student_file": str(sf.name),
        "grades_file": f"grades_matrix_{class_name}.csv",
        "meta_file": f"assignments_meta_{class_name}.csv",
        "files": sorted([p.name for p in backup_dir.iterdir() if p.is_file()]),
    }
    with open(backup_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return backup_dir


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

# =======================
# Sauvegardes (sidebar)
# =======================
with st.sidebar.expander("Sauvegardes"):
    st.caption("Crée un instantané horodaté des fichiers de la classe (notes, métadonnées, liste d'élèves).")
    if st.button("Créer une sauvegarde maintenant"):
        try:
            backup_dir = make_backup(
                class_name=class_name,
                student_file=student_file,
                grades_file=grades_file,
                meta_file=meta_file,
                grade_matrix=st.session_state.get("grade_matrix"),
                meta_df=st.session_state.get("assignment_meta"),
                data_dir=DATA_DIR,
            )
            st.success(f"Sauvegarde créée : {backup_dir}")
        except Exception as e:
            st.error("Échec de la sauvegarde.")
            st.exception(e)

    # Liste des 5 dernières sauvegardes pour cette classe
    base = Path(DATA_DIR) / "backups" / class_name
    if base.exists():
        last = sorted([p for p in base.iterdir() if p.is_dir()], reverse=True)[:5]
        if last:
            st.write("Sauvegardes récentes :")
            for p in last:
                st.write(f"- {p.name}")
    else:
        st.caption("Aucune sauvegarde pour cette classe pour le moment.")


# ======================================
# Tableau complet de la classe (en premier)
# ======================================
st.title("Trimesta — Suivi des évaluations")
st.subheader(f"Tableau des notes — Classe {class_name}")
st.dataframe(sanitize_for_display(grade_matrix))


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

# --- Gestion de l’évaluation sélectionnée (renommer / supprimer) ---
def _backup_csv(path_like):
    """Crée une sauvegarde .bak horodatée du CSV avant modification."""
    p = Path(path_like)
    if p.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = p.with_suffix(p.suffix + f".bak-{ts}")
        try:
            shutil.copy(p, backup)
        except Exception:
            pass  # pas bloquant

# Seulement si au moins 1 évaluation existe et qu’on n’est pas sur "➕ Nouvelle évaluation"
assignments = [col for col in grade_matrix.columns if col != "Full Name"]
if assignments and selected_assignment != "➕ Nouvelle évaluation":

    with st.expander("Gérer l’évaluation sélectionnée"):
        c1, c2 = st.columns(2)

        # -------- Renommer --------
        with c1:
            st.write("Renommer l’évaluation")
            new_name = st.text_input(
                "Nouveau nom",
                value=selected_assignment,
                key="rename_eval_input",
            )
            if st.button("Renommer", key="btn_rename_eval"):
                new_name = (new_name or "").strip()
                if not new_name:
                    st.warning("Veuillez saisir un nouveau nom.")
                elif new_name == selected_assignment:
                    st.info("Le nom est inchangé.")
                elif new_name in grade_matrix.columns:
                    st.error("Une évaluation porte déjà ce nom.")
                else:
                    # Sauvegardes
                    _backup_csv(grades_file)
                    _backup_csv(meta_file)

                    # Renommer la colonne dans la matrice
                    grade_matrix = grade_matrix.rename(columns={selected_assignment: new_name})
                    st.session_state["grade_matrix"] = grade_matrix

                    # Mettre à jour la méta (Assignment)
                    if not meta_df.empty and "Assignment" in meta_df.columns:
                        meta_df.loc[meta_df["Assignment"] == selected_assignment, "Assignment"] = new_name
                        st.session_state["assignment_meta"] = meta_df

                    # Sauvegarde sur disque
                    grade_matrix.to_csv(grades_file, index=False)
                    meta_df.to_csv(meta_file, index=False)

                    st.success(f"Évaluation renommée en « {new_name} ».")
                    st.rerun()

        # -------- Supprimer --------
        with c2:
            st.write("Supprimer l’évaluation")
            non_null = int(grade_matrix[selected_assignment].count())
            st.caption(f"Valeurs non vides dans cette colonne : {non_null}")
            confirm = st.checkbox("Je confirme la suppression définitive", key="confirm_delete_eval")

            if st.button("Supprimer", key="btn_delete_eval"):
                if not confirm:
                    st.warning("Cochez la case de confirmation pour supprimer.")
                else:
                    # Sauvegardes
                    _backup_csv(grades_file)
                    _backup_csv(meta_file)

                    # Supprimer la colonne de la matrice
                    grade_matrix = grade_matrix.drop(columns=[selected_assignment])
                    st.session_state["grade_matrix"] = grade_matrix

                    # Retirer la ligne de méta correspondante
                    if not meta_df.empty and "Assignment" in meta_df.columns:
                        meta_df = meta_df[meta_df["Assignment"] != selected_assignment].copy()
                        st.session_state["assignment_meta"] = meta_df

                    # Sauvegarde sur disque
                    grade_matrix.to_csv(grades_file, index=False)
                    meta_df.to_csv(meta_file, index=False)

                    st.success("Évaluation supprimée.")
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
        name_col = _name_col(grade_matrix)
        student_name = st.selectbox(
            "Choisir un élève",
            grade_matrix[name_col].tolist(),
            key="student_name_selectbox",
        )
        student_row = grade_matrix[grade_matrix[name_col] == student_name]

        if not student_row.empty:
            # Afficher proprement les notes par évaluation (sans la colonne du nom)
            assignments_only = student_row.drop(columns=[name_col], errors="ignore")
            series = pd.to_numeric(assignments_only.squeeze(), errors="coerce")
            display_df = series.to_frame(name=student_name)  # une colonne, que des floats/NaN
            st.write("Notes par évaluation :")
            st.dataframe(display_df)

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
    with st.expander("Options histogramme"):
        fixed = st.checkbox("Échelle X fixe de 0 à 6", value=False)
        y_choice = st.radio("Échelle Y", ["Auto", "Taille de la classe"], horizontal=True, index=0)
    plot_grade_distribution(
        grade_matrix,
        title=f"Répartition des notes — Classe {class_name}",
        fixed_scale=fixed,
        y_mode=("class" if y_choice == "Taille de la classe" else "auto"),
    )

if st.checkbox("Afficher le boxplot des notes par évaluation"):
    plot_grades_by_assignment(grade_matrix)

if st.checkbox("Afficher la moyenne de la classe par évaluation et par trimestre"):
    plot_class_trimester_summary(grade_matrix, meta_df)

if st.checkbox("Afficher l’évolution des notes d’un élève"):
    name = st.selectbox("Sélectionner un élève", grade_matrix["Full Name"].tolist(), key="progress_name")
    plot_student_progress(grade_matrix, name)
