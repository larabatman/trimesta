import pandas as pd
from pathlib import Path

def load_students(file_path: str) -> pd.DataFrame:
    """Charge la liste des élèves depuis un fichier Excel.

    Accepte des colonnes en anglais ('First Name', 'Last Name') ou en français ('Prénom', 'Nom').
    Crée toujours les colonnes internes 'Full Name' et 'ID'.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier des élèves introuvable : {file_path}")

    df = pd.read_excel(path)

    # Normalise les noms présents (gestion accents/casse/espaces)
    normalized = {c.strip().lower(): c for c in df.columns}

    # Cherche colonnes prénom / nom (anglais/français)
    first_candidates = [k for k in normalized if k in ("first name", "prénom", "prenom")]
    last_candidates  = [k for k in normalized if k in ("last name", "nom")]

    if not first_candidates or not last_candidates:
        raise ValueError(
            "Le fichier Excel doit contenir les colonnes "
            "'First Name' et 'Last Name' ou 'Prénom' et 'Nom'."
        )

    first_col = normalized[first_candidates[0]]
    last_col  = normalized[last_candidates[0]]

    df["Full Name"] = df[first_col].astype(str).str.strip() + " " + df[last_col].astype(str).str.strip()
    df["ID"] = df.index

    return df  # on retourne le DataFrame complet avec les colonnes ajoutées


def save_grades(df: pd.DataFrame, file_path: str):
    """Enregistre les notes dans un fichier CSV."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)


def load_grades(file_path: str) -> pd.DataFrame:
    """Charge un CSV de notes (schéma ancien 'ligne par note') et
    normalise les colonnes vers ['ID', 'Full Name', 'Grade', 'Coefficient', 'Trimester'].

    Accepte également les noms français : 'Nom complet', 'Note', 'Trimestre'.
    """
    path = Path(file_path)
    expected_cols = ["ID", "Full Name", "Grade", "Coefficient", "Trimester"]

    if not path.exists():
        return pd.DataFrame(columns=expected_cols)

    df = pd.read_csv(path)

    # Mapping FR/EN -> colonnes internes
    lower_map = {c.strip().lower(): c for c in df.columns}
    mapping = {
        "id": "ID",
        "full name": "Full Name",
        "nom complet": "Full Name",
        "grade": "Grade",
        "note": "Grade",
        "coefficient": "Coefficient",
        "trimester": "Trimester",
        "trimestre": "Trimester",
    }

    rename_dict = {}
    for k, target in mapping.items():
        if k in lower_map:
            rename_dict[lower_map[k]] = target

    df = df.rename(columns=rename_dict)

    # Ajoute les colonnes manquantes si besoin
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df[expected_cols]
