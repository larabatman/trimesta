import pandas as pd
from pathlib import Path
import unicodedata
import re

# --- utilitaires de normalisation ---

def _norm_text(s) -> str:
    """Normalise un texte pour la comparaison: minuscules, sans accents, espaces trim."""
    s = "" if s is None else str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower()

def _find_header_row(df: pd.DataFrame, max_scan: int = 50) -> int:
    """
    Trouve l'index de la ligne d'entête en cherchant une ligne contenant au moins
    'nom' ET ('prenom' OU 'first name').
    Lit un DataFrame lu avec header=None.
    """
    rows = min(max_scan, len(df))
    for i in range(rows):
        row_vals = [_norm_text(v) for v in df.iloc[i].tolist()]
        row_vals = [v for v in row_vals if v != ""]
        if not row_vals:
            continue
        has_nom = any(v == "nom" for v in row_vals)
        has_prenom = any(v in ("prenom", "prénom", "first name", "firstname", "first") for v in row_vals)
        if has_nom and has_prenom:
            return i
    # Plan B: ligne contenant 'full name' / 'nom complet'
    for i in range(rows):
        row_vals = [_norm_text(v) for v in df.iloc[i].tolist()]
        if any(v in ("full name", "nom complet", "nomcomplet") for v in row_vals):
            return i
    raise ValueError("Impossible de localiser la ligne d'entête (Nom / Prénom).")

def _strip_vowels_keep_first(s: str) -> str:
    """Optionnel: retirer les voyelles en conservant la 1re lettre (si tu veux anonymiser ici)."""
    if not isinstance(s, str) or s == "":
        return s
    vowels = set("aeiouyAEIOUY"
                 "àáâãäåÀÁÂÃÄÅ"
                 "èéêëÈÉÊË"
                 "ìíîïÌÍÎÏ"
                 "òóôõöÒÓÔÕÖ"
                 "ùúûüÙÚÛÜ"
                 "ÿŸ")
    out = [s[0]]
    for ch in s[1:]:
        if ch in vowels:
            continue
        out.append(ch)
    return "".join(out)

# --- API ---

def load_students(
    file_path: str,
    *,
    anonymize_last: bool = False,   # ton .xls arrive déjà anonymisé ; laisse False par défaut
    keep_raw_last: bool = True      # on conserve les colonnes d'origine
) -> pd.DataFrame:
    """
    Charge une liste d'élèves depuis un .xls / .xlsx avec entêtes possiblement décalées.
    Construit 'Full Name' à partir de 'Prénom' + 'Nom' ou utilise 'Full Name' existant.

    - Supporte les entêtes FR/EN: Nom/Prénom ou Last Name/First Name ou Full Name/Nom complet
    - Si anonymize_last=True, on retire les voyelles du Nom (en gardant la 1re lettre)
    - Crée 'ID' à partir de la colonne 'No' si présente, sinon index.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier des élèves introuvable : {file_path}")

    read_kwargs = {"header": None}
    if path.suffix.lower() == ".xls":
        read_kwargs["engine"] = "xlrd"

    try:
        raw = pd.read_excel(path, **read_kwargs)
    except Exception as e:
        raise RuntimeError(
            f"Impossible de lire le fichier Excel '{file_path}'. "
            f"Pour .xls, installez xlrd (pip install xlrd). "
            f"Erreur : {e}"
        )

    # Détecte la ligne d'entête et reconstruit le DF avec de "vrais" noms de colonnes
    hdr_idx = _find_header_row(raw)
    header = raw.iloc[hdr_idx].astype(str).tolist()
    df = raw.iloc[hdr_idx + 1 :].copy()
    df.columns = header
    # Drop lignes totalement vides
    df = df.dropna(how="all").reset_index(drop=True)

    # Normalise un mapping des colonnes pour retrouver Prénom/Nom (et variantes)
    colmap = {_norm_text(c): c for c in df.columns}
    # Cherche Prénom / First Name
    first_key = None
    for k in ("prénom", "prenom", "first name", "firstname", "first"):
        if k in colmap:
            first_key = colmap[k]
            break
    # Cherche Nom / Last Name
    last_key = None
    for k in ("nom", "last name", "lastname", "last"):
        if k in colmap:
            last_key = colmap[k]
            break
    # Ou colonne Full Name / Nom complet
    full_key = None
    for k in ("full name", "nom complet", "nomcomplet"):
        if k in colmap:
            full_key = colmap[k]
            break

    if first_key and last_key:
        first = df[first_key].astype(str).str.strip()
        last = df[last_key].astype(str).str.strip()
        if anonymize_last:
            last = last.apply(_strip_vowels_keep_first)
        df["Full Name"] = first + " " + last
        if not keep_raw_last:
            df = df.drop(columns=[last_key])
    elif full_key:
        df["Full Name"] = df[full_key].astype(str).str.strip()
    else:
        raise ValueError(
            "Le fichier Excel doit contenir soit 'Prénom' et 'Nom' (ou 'First Name' et 'Last Name'), "
            "soit une colonne 'Full Name'/'Nom complet'."
        )

    # Crée ID : on privilégie la colonne 'No' si présente, sinon l'index
    id_key = None
    for k in ("no", "n°", "num", "numero", "number", "nr"):
        if k in colmap:
            id_key = colmap[k]
            break
    if id_key and id_key in df.columns:
        # On tente de convertir proprement
        df["ID"] = pd.to_numeric(df[id_key], errors="coerce")
        # S'il y a des NaN, fallback sur l'index
        if df["ID"].isna().any():
            df["ID"] = range(len(df))
    else:
        df["ID"] = range(len(df))

    # Nettoie Full Name (évite "nan nan")
    df["Full Name"] = df["Full Name"].str.replace(r"\s+", " ", regex=True).str.strip()

    return df


def save_grades(df: pd.DataFrame, file_path: str):
    """Enregistre la matrice/les notes dans un CSV (création du dossier si besoin)."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)


def load_grades(file_path: str) -> pd.DataFrame:
    """
    (Legacy "ligne par note") Charge un CSV de notes et normalise les colonnes internes :
    ['ID', 'Full Name', 'Grade', 'Coefficient', 'Trimester'].
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

    # Colonnes manquantes si besoin
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df[expected_cols]
