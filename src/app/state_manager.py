import os
import pandas as pd
import streamlit as st

def init_session_state_matrix(grades_path: str, students_df: pd.DataFrame, class_name: str):
    """
    Initialise dans st.session_state les éléments suivants pour la classe sélectionnée :
      - 'grade_matrix'     : DataFrame (lignes = élèves, colonnes = évaluations)
      - 'assignment_meta'  : métadonnées des évaluations (Assignment, Coefficient, Trimester)
      - 'grades_file'      : chemin du CSV de la matrice de notes
      - 'current_class'    : identifiant/nom de la classe courante

    Comportement :
      - Recharge si la classe change OU si 'grade_matrix' est absent.
      - Si le CSV n'existe pas, crée une matrice ne contenant que la colonne 'Full Name'
        à partir de students_df.
      - Aligne la matrice avec la liste des élèves (ajoute les nouveaux élèves si besoin).
    """
    if st.session_state.get("current_class") != class_name or "grade_matrix" not in st.session_state:
        # --- Charger ou initialiser la matrice de notes ---
        if os.path.exists(grades_path):
            df = pd.read_csv(grades_path)
        else:
            # On part de la liste d'élèves (load_students crée 'Full Name')
            df = pd.DataFrame({"Full Name": students_df["Full Name"].astype(str).tolist()})

        # S'assurer que la colonne du nom est 'Full Name' (gère quelques variantes FR)
        if "Full Name" not in df.columns:
            for alt in ["Nom complet", "Nom Complet", "Nom"]:
                if alt in df.columns:
                    df = df.rename(columns={alt: "Full Name"})
                    break

        # Normaliser le type de la colonne et aligner avec la liste d'élèves actuelle
        df["Full Name"] = df["Full Name"].astype(str)
        current_names = students_df["Full Name"].astype(str)

        # Ajouter les élèves manquants (nouveaux arrivés dans le fichier Excel)
        missing = current_names[~current_names.isin(df["Full Name"])]
        if not missing.empty:
            df = pd.concat([df, pd.DataFrame({"Full Name": missing.tolist()})], ignore_index=True)

        # (Optionnel) Trier par nom pour une lecture plus claire
        df = df.sort_values(by=["Full Name"]).reset_index(drop=True)

        st.session_state["grade_matrix"] = df
        st.session_state["grades_file"] = grades_path

        # --- Charger les métadonnées des évaluations ---
        meta_file = f"data/assignments_meta_{class_name}.csv"
        if os.path.exists(meta_file):
            meta_df = pd.read_csv(meta_file)
        else:
            meta_df = pd.DataFrame(columns=["Assignment", "Coefficient", "Trimester"])
        st.session_state["assignment_meta"] = meta_df  # requis pour l'app

        # --- Suivre la classe courante ---
        st.session_state["current_class"] = class_name
