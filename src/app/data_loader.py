# src/app/data_loader.py
import pandas as pd
from pathlib import Path
import unicodedata

# ---------- helpers ----------

def _norm_text(s) -> str:
    """Lowercase, strip, remove accents (for robust matching)."""
    s = "" if s is None else str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower()

def _find_header_row(df: pd.DataFrame, max_scan: int = 50) -> int:
    """
    Find the header row by scanning for a line that contains both
    'Nom' and ('Prénom' or 'First Name'). DataFrame is read with header=None.
    """
    rows = min(max_scan, len(df))
    for i in range(rows):
        vals = [_norm_text(v) for v in df.iloc[i].tolist()]
        vals = [v for v in vals if v]
        if not vals:
            continue
        has_nom = any(v == "nom" for v in vals)
        has_prenom = any(v in ("prenom", "prénom", "first name", "firstname", "first") for v in vals)
        if has_nom and has_prenom:
            return i
    # fallback: row containing 'full name' / 'nom complet'
    for i in range(rows):
        vals = [_norm_text(v) for v in df.iloc[i].tolist()]
        if any(v in ("full name", "nom complet", "nomcomplet") for v in vals):
            return i
    raise ValueError("Impossible de localiser la ligne d'entête (Nom / Prénom).")

_VOWELS = set(list("aeiouyAEIOUY")
              + list("àáâãäåÀÁÂÃÄÅ")
              + list("èéêëÈÉÊË")
              + list("ìíîïÌÍÎÏ")
              + list("òóôõöÒÓÔÕÖ")
              + list("ùúûüÙÚÛÜ")
              + list("ÿŸ"))

def _strip_vowels_keep_first(s: str) -> str:
    """Remove vowels from a string but keep the very first character."""
    if not isinstance(s, str) or s == "":
        return s
    out = [s[0]]
    for ch in s[1:]:
        if ch in _VOWELS:
            continue
        out.append(ch)
    return "".join(out)

# ---------- public API ----------

def load_students(file_path: str) -> pd.DataFrame:
    """
    Load class list from .xls/.xlsx with possible pre-header lines.
    ALWAYS anonymizes the last name by stripping vowels (preserves first letter).
    Builds 'Full Name' and adds 'ID'.

    Accepts FR/EN headers:
      - 'Nom'/'Prénom' or 'Last Name'/'First Name', or a single 'Full Name'/'Nom complet'.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier des élèves introuvable : {file_path}")

    read_kwargs = {"header": None}
    if path.suffix.lower() == ".xls":
        # requires xlrd in requirements
        read_kwargs["engine"] = "xlrd"

    try:
        raw = pd.read_excel(path, **read_kwargs)
    except Exception as e:
        raise RuntimeError(
            f"Impossible de lire le fichier Excel '{file_path}'. "
            f"Pour .xls, installez xlrd (pip install xlrd). "
            f"Erreur : {e}"
        )

    hdr_idx = _find_header_row(raw)
    header = raw.iloc[hdr_idx].astype(str).tolist()
    df = raw.iloc[hdr_idx + 1 :].copy()
    df.columns = header
    df = df.dropna(how="all").reset_index(drop=True)

    # map columns for FR/EN names
    colmap = {_norm_text(c): c for c in df.columns}

    first_key = next((colmap[k] for k in ("prénom", "prenom", "first name", "firstname", "first") if k in colmap), None)
    last_key  = next((colmap[k] for k in ("nom", "last name", "lastname", "last") if k in colmap), None)
    full_key  = next((colmap[k] for k in ("full name", "nom complet", "nomcomplet") if k in colmap), None)

    if first_key and last_key:
        first = df[first_key].astype(str).str.strip()
        last  = df[last_key].astype(str).str.strip()
        # ALWAYS anonymize last name (idempotent if already anonymized)
        last_anon = last.apply(_strip_vowels_keep_first)
        df["Full Name"] = (first + " " + last_anon).str.replace(r"\s+", " ", regex=True).str.strip()
    elif full_key:
        # Anonymize the last token of Full Name (keeps first letter)
        def _anon_full(full: str) -> str:
            full = str(full).strip()
            if not full:
                return full
            parts = full.split()
            if len(parts) == 1:
                return _strip_vowels_keep_first(parts[0])
            first = " ".join(parts[:-1])
            last  = parts[-1]
            return (first + " " + _strip_vowels_keep_first(last)).strip()

        df["Full Name"] = df[full_key].astype(str).apply(_anon_full)
    else:
        raise ValueError(
            "Le fichier Excel doit contenir soit 'Prénom' et 'Nom' (ou 'First Name' et 'Last Name'), "
            "soit une colonne 'Full Name'/'Nom complet'."
        )

    # ID: prefer 'No' if present, else use index
    id_key = next((colmap[k] for k in ("no", "n°", "num", "numero", "number", "nr") if k in colmap), None)
    if id_key and id_key in df.columns:
        df["ID"] = pd.to_numeric(df[id_key], errors="coerce")
        if df["ID"].isna().any():
            df["ID"] = range(len(df))
    else:
        df["ID"] = range(len(df))

    return df[["Full Name", "ID"]].join(
        df.drop(columns=[c for c in ["Full Name", "ID"] if c in df.columns], errors="ignore")
    , how="left")
    # Note: returning all original columns too can be useful; keep as-is if preferred.

def save_grades(df: pd.DataFrame, file_path: str):
    """Save grades/matrix to CSV (ensure directory exists)."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)

def load_grades(file_path: str) -> pd.DataFrame:
    """
    Legacy row-per-grade loader; normalizes to:
    ['ID', 'Full Name', 'Grade', 'Coefficient', 'Trimester'].
    """
    path = Path(file_path)
    expected = ["ID", "Full Name", "Grade", "Coefficient", "Trimester"]
    if not path.exists():
        return pd.DataFrame(columns=expected)

    df = pd.read_csv(path)
    lower = {c.strip().lower(): c for c in df.columns}
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
    rename = {lower[k]: v for k, v in mapping.items() if k in lower}
    df = df.rename(columns=rename)
    for col in expected:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    return df[expected]