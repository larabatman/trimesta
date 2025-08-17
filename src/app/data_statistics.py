import pandas as pd

# --- Petits utilitaires de normalisation -------------------------------

def _normalize_name_column(df: pd.DataFrame) -> str:
    """Retourne le nom de la colonne à utiliser pour le nom complet de l'élève."""
    candidates = ["Full Name", "Nom complet", "Nom Complet", "Nom"]
    for c in candidates:
        if c in df.columns:
            return c
    # Par défaut, on suppose 'Full Name' (la plupart du temps créé par load_students)
    return "Full Name"

def _normalize_meta_columns(meta_df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomme les colonnes du méta-dataframe d'évaluations en anglais interne :
    - Assignment  <- { "Assignment", "Évaluation", "Evaluation" }
    - Coefficient <- { "Coefficient", "Pondération", "Ponderation" }
    - Trimester   <- { "Trimester", "Trimestre" }
    """
    if meta_df is None or meta_df.empty:
        return pd.DataFrame(columns=["Assignment", "Coefficient", "Trimester"])

    mapping = {}
    lower_map = {c.strip().lower(): c for c in meta_df.columns}

    def _pick(source_names, target):
        for s in source_names:
            if s.lower() in lower_map:
                mapping[lower_map[s.lower()]] = target
                return

    _pick(["Assignment", "Évaluation", "Evaluation"], "Assignment")
    _pick(["Coefficient", "Pondération", "Ponderation"], "Coefficient")
    _pick(["Trimester", "Trimestre"], "Trimester")

    meta = meta_df.rename(columns=mapping).copy()

    # Ajoute colonnes manquantes si besoin
    for col in ["Assignment", "Coefficient", "Trimester"]:
        if col not in meta.columns:
            meta[col] = pd.Series(dtype="object")

    return meta[["Assignment", "Coefficient", "Trimester"]]


# --- Fonctions principales --------------------------------------------

def compute_student_weighted_average(
    grade_matrix: pd.DataFrame,
    meta_df: pd.DataFrame,
    student_name: str
):
    """
    Calcule la moyenne pondérée d’un élève à partir des coefficients d’évaluations.
    Retourne un float (arrondi à 2 décimales) ou None si non calculable.
    Accepte des colonnes FR/EN pour les métadonnées (Évaluation/Trimestre/…).
    """
    if grade_matrix is None or grade_matrix.empty:
        return None

    name_col = _normalize_name_column(grade_matrix)
    if name_col not in grade_matrix.columns:
        return None

    row = grade_matrix[grade_matrix[name_col] == student_name]
    if row.empty or row.shape[1] <= 1:
        return None

    # Série des notes (toutes les colonnes sauf le nom)
    grades = row.drop(columns=[name_col]).squeeze()

    # S’assure qu’on a une Series (et pas un scalaire / NA)
    if not isinstance(grades, pd.Series):
        return None

    # Évaluations avec des valeurs numériques
    valid_assignments = grades.dropna().index.tolist()
    if not valid_assignments:
        return None

    # Normalise les colonnes du méta-dataframe
    meta = _normalize_meta_columns(meta_df).set_index("Assignment")

    # Restreint le méta aux évaluations présentes
    meta = meta.reindex(valid_assignments)

    # Coeffs (défaut 1.0)
    weights = pd.to_numeric(meta["Coefficient"], errors="coerce").fillna(1.0)

    # Valeurs des notes (numériques)
    values = pd.to_numeric(grades[valid_assignments], errors="coerce")
    mask = values.notna() & weights.notna()

    values = values[mask]
    weights = weights[mask]

    if values.empty or weights.sum() == 0:
        return None

    weighted_avg = (values * weights).sum() / weights.sum()
    return round(float(weighted_avg), 2)


def compute_trimester_averages(
    grade_matrix: pd.DataFrame,
    meta_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcule les moyennes pondérées par élève pour chaque trimestre (T1, T2, T3)
    ainsi que la moyenne globale.
    Retourne un DataFrame :
        | Full Name       | T1   | T2   | T3   | Global |
    Accepte des colonnes FR/EN pour les métadonnées.
    """
    if grade_matrix is None or grade_matrix.empty:
        return pd.DataFrame(columns=["Full Name", "T1", "T2", "T3", "Global"])

    name_col = _normalize_name_column(grade_matrix)
    if name_col not in grade_matrix.columns:
        return pd.DataFrame(columns=["Full Name", "T1", "T2", "T3", "Global"])

    result = { "Full Name": grade_matrix[name_col] }
    student_names = grade_matrix[name_col].tolist()

    # Normalise métadonnées
    meta = _normalize_meta_columns(meta_df).copy()

    # Conserve uniquement les évaluations qui existent dans la matrice
    existing_assignments = [c for c in grade_matrix.columns if c != name_col]
    meta = meta[meta["Assignment"].isin(existing_assignments)]

    # --- Par trimestre ---
    for trimester in ["T1", "T2", "T3"]:
        trimester_assignments = meta[meta["Trimester"] == trimester]["Assignment"].tolist()

        if not trimester_assignments:
            result[trimester] = [None] * len(student_names)
            continue

        # Coefficients du trimestre (défaut 1.0)
        coefs = pd.to_numeric(
            meta.set_index("Assignment").loc[trimester_assignments]["Coefficient"],
            errors="coerce"
        ).fillna(1.0)

        # Sous-matrice {nom + colonnes d’évaluations du trimestre}
        subset_cols = [name_col] + trimester_assignments
        trimester_grades = grade_matrix[subset_cols].copy()

        trimester_averages = []
        for _, row in trimester_grades.iterrows():
            grades = pd.to_numeric(row[trimester_assignments], errors="coerce")
            valid_mask = grades.notna()
            values = grades[valid_mask]
            weights = coefs[valid_mask]

            if values.empty or weights.sum() == 0:
                trimester_averages.append(None)
            else:
                avg = (values * weights).sum() / weights.sum()
                trimester_averages.append(round(float(avg), 2))

        result[trimester] = trimester_averages

    # --- Moyenne globale (toutes évaluations disponibles) ---
    global_averages = []
    all_assignments = meta["Assignment"].tolist()

    if all_assignments:
        coefs_all = pd.to_numeric(
            meta.set_index("Assignment")["Coefficient"], errors="coerce"
        ).fillna(1.0)

        for _, row in grade_matrix.iterrows():
            grades = pd.to_numeric(row[all_assignments], errors="coerce")
            valid_mask = grades.notna()
            values = grades[valid_mask]
            weights = coefs_all[valid_mask]

            if values.empty or weights.sum() == 0:
                global_averages.append(None)
            else:
                avg = (values * weights).sum() / weights.sum()
                global_averages.append(round(float(avg), 2))
    else:
        global_averages = [None] * len(student_names)

    result["Global"] = global_averages

    # On garde 'Full Name' comme clé interne pour compatibilité
    return pd.DataFrame(result, columns=["Full Name", "T1", "T2", "T3", "Global"])
