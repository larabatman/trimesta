# Trimesta — Gestion de notes par évaluations (Streamlit)

Trimesta est une application Streamlit pour gérer les notes d’une classe, centrée sur les **évaluations** (assignments).
Elle permet de créer des évaluations avec coefficient et trimestre, d’attribuer la même note à plusieurs élèves, de calculer des moyennes pondérées (par élève, par trimestre, globale) et d’afficher des visualisations.

## Sommaire

* [Fonctionnalités](#fonctionnalités)
* [Architecture](#architecture)
* [Prérequis](#prérequis)
* [Installation et lancement](#installation-et-lancement)
* [Organisation des données](#organisation-des-données)

  * [Fichiers élèves](#fichiers-élèves)
  * [Matrice de notes](#matrice-de-notes)
  * [Méta-données des évaluations](#méta-données-des-évaluations)
* [Utilisation](#utilisation)

  * [1) Choisir la classe](#1-choisir-la-classe)
  * [2) Ajouter une évaluation](#2-ajouter-une-évaluation)
  * [3) Attribuer des notes](#3-attribuer-des-notes)
  * [4) Annuler la dernière attribution](#4-annuler-la-dernière-attribution)
  * [5) Analyse par élève](#5-analyse-par-élève)
  * [6) Synthèses par trimestre et visualisations](#6-synthèses-par-trimestre-et-visualisations)
* [Validation et règles métier](#validation-et-règles-métier)
* [Thème “cahier” (optionnel)](#thème-cahier-optionnel)
* [Internationalisation](#internationalisation)
* [Conseils et limitations](#conseils-et-limitations)
* [Feuille de route](#feuille-de-route)
* [Licence](#licence)

---

## Fonctionnalités

* **Centrée évaluations** : chaque évaluation devient une **colonne** dans une matrice (lignes = élèves).
* **Coefficient et trimestre** pour chaque évaluation (T1, T2, T3).
* **Saisie groupée** : attribuer la même note à plusieurs élèves en une fois.
* **Annuler la dernière attribution** d’un simple clic.
* **Moyennes pondérées** :

  * par élève (tous trimestres),
  * par trimestre (T1/T2/T3),
  * globale.
* **Visualisations** :

  * histogramme global des notes,
  * boxplot des notes par évaluation,
  * progression d’un élève,
  * moyenne de classe par évaluation et par trimestre.
* **Tolérance colonnes FR/EN** pour les fichiers Excel et métadonnées.
* **Décimales** : point ou virgule acceptés (ex. `4.5` ou `4,5`).

---

## Architecture

```
repo/
├─ src/
│  ├─ trimesta.py                  # Application principale Streamlit (UI)
│  └─ app/
│     ├─ data_loader.py            # Chargement élèves + (legacy) notes; sauvegarde CSV
│     ├─ state_manager.py          # Initialisation session/matrice/métadonnées
│     ├─ data_statistics.py        # Moyennes pondérées (élève, trimestres, global)
│     ├─ data_visualization.py     # Graphiques (histogramme, boxplot, progression, synthèse trimestres)
│     └─ ui_components.py          # (optionnel) Formulaire de saisie (mode legacy)
├─ data/
│  ├─ 901.xlsx                     # Fichier élèves (exemple)
│  ├─ 706.xlsx                     # Fichier élèves (exemple)
│  ├─ grades_matrix_901.csv        # Matrice de notes générée (optionnel)
│  └─ assignments_meta_901.csv     # Métadonnées d’évaluations (coeff, trimestre)
└─ requirements.txt
```

---

## Prérequis

* Python 3.9+ (3.11/3.12 OK)
* macOS, Linux ou Windows
* Outils standard (terminal, pip)

---

## Installation et lancement

```bash
# 1) Cloner le dépôt
git clone <votre-repo.git>
cd <votre-repo>

# 2) Environnement virtuel (recommandé)
python -m venv .venv
source .venv/bin/activate         # macOS/Linux
# .venv\Scripts\activate          # Windows

# 3) Dépendances
pip install -r requirements.txt

# 4) Lancer l’app
streamlit run src/trimesta.py
```

> `requirements.txt` (suggestion) :
>
> ```
> streamlit
> pandas
> openpyxl
> matplotlib
> seaborn
> ```

---

## Organisation des données

### Fichiers élèves

Dans `data/`, un fichier Excel **par classe**, nommé par exemple `901.xlsx`, `706.xlsx`, etc.

Colonnes acceptées (FR/EN) :

* `First Name` / `Prénom`
* `Last Name`  / `Nom`

L’app crée automatiquement :

* `Full Name` (concaténation),
* `ID` (index).

Exemple minimal (Excel) :

|  Prénom | Nom         |
| ------: | ----------- |
| Camille | Lefèvre     |
|    Théo | Charpentier |

### Matrice de notes

* Fichier CSV par classe : `grades_matrix_{classe}.csv`
* Lignes = élèves (`Full Name`)
* Colonnes = évaluations (`Évaluation 1`, `Dictée 12`, …)
* Créé automatiquement si absent.

### Méta-données des évaluations

* Fichier CSV par classe : `assignments_meta_{classe}.csv`
* Colonnes : `Assignment`, `Coefficient`, `Trimester`
* Créé/complété automatiquement via l’UI.

---

## Utilisation

### 1) Choisir la classe

* Dans la barre latérale, choisir une classe parmi les fichiers `*.xlsx` présents dans `data/`.

### 2) Ajouter une évaluation

* Menu déroulant « Sélectionner ou ajouter une évaluation » → « ➕ Nouvelle évaluation »
* Saisir le nom, le **coefficient** (pondération), le **trimestre** (T1/T2/T3)
* Valider avec « Créer l’évaluation »

> Une colonne est ajoutée à la matrice de notes et une ligne est ajoutée au fichier `assignments_meta_{classe}.csv`.

### 3) Attribuer des notes

* Choisir l’évaluation courante
* Sélectionner un ou plusieurs élèves
* Saisir la note (ex. `4,5`), puis « Attribuer la note »

> Les champs « élèves sélectionnés » et « note » se remettent à zéro automatiquement après attribution.

### 4) Annuler la dernière attribution

* Ouvrir « Annuler la dernière attribution »
* Cliquer sur « Annuler cette attribution »

> Supprime les notes posées lors de la dernière action et met à jour la matrice.

### 5) Analyse par élève

* Ouvrir « Analyse par élève »
* Choisir un élève, consulter ses notes, sa **moyenne pondérée** (affichée avec 2 décimales et arrondie au **dixième**).

### 6) Synthèses par trimestre et visualisations

* **Synthèses par trimestre** : tableau des moyennes pondérées T1/T2/T3 + globale.
* **Histogramme** des notes.
* **Boxplot** par évaluation (+ points individuels).
* **Moyenne par évaluation et par trimestre** (courbes T1/T2/T3).
* **Progression d’un élève** (courbe).

---

## Validation et règles métier

* Notes acceptées : **réels de 0 à 6** (inclus).
* Séparateur décimal : **virgule** ou **point**.
* L’arrondi de la note saisie peut être affiché au **dixième** côté UI.
* La moyenne pondérée est calculée à partir des **coefficients** saisis dans les métadonnées.
* En l’absence d’évaluations pour un trimestre, la moyenne du trimestre est `None`.

---

## Thème “cahier” (optionnel)

Créer `.streamlit/config.toml` à la racine :

```toml
[theme]
primaryColor = "#D97706"
backgroundColor = "#FFFDF6"
secondaryBackgroundColor = "#F1F0E8"
textColor = "#3B3A30"
font = "serif"
```

---

## Internationalisation

* L’interface principale est en **français**.
* Les modules tolèrent colonnes **FR ou EN** :

  * Éléves : `First Name`/`Last Name` ou `Prénom`/`Nom`
  * Métadonnées : `Assignment`/`Évaluation`, `Coefficient`/`Pondération`, `Trimester`/`Trimestre`
* En interne, l’app standardise vers `Full Name`, `Assignment`, `Coefficient`, `Trimester`.

---

## Conseils et limitations

* **Sauvegarde** : la matrice est enregistrée à chaque attribution/annulation (`grades_matrix_{classe}.csv`).
* **Synchronisation élèves** : si vous ajoutez des élèves dans `*.xlsx`, l’app les ajoute automatiquement à la matrice.
* **Suppression d’élèves** : non automatique (pour éviter les pertes). À décider selon votre usage.
* **Éditions directes** : l’édition cellule par cellule dans la matrice depuis l’UI n’est pas activée. À envisager via une fonctionnalité dédiée.
* **Annuler** : l’undo porte sur **la dernière action groupée**.

---

## Feuille de route

* Suppression/édition d’une note **au choix** dans la matrice.
* Export PDF/Excel des bulletins (par élève / par classe).
* Filtrage/affichage par matière ou type d’évaluation (si vous ajoutez ce champ).
* Journal des modifications (audit log).
* Authentification simple (si déploiement multi-professeurs).

---

## Licence

À définir par le propriétaire du dépôt (ex. MIT).

---

## Modules — résumé rapide

* `src/trimesta.py`
  UI principale Streamlit. Sélection classe, création évaluations, saisie groupée, undo, analyses, graphiques.

* `app/data_loader.py`
  Chargement élèves (FR/EN), création `Full Name`/`ID`.
  Fonctions legacy de chargement/sauvegarde de notes au format “ligne par note”.

* `app/state_manager.py`
  Initialisation de la **matrice de notes** et des **métadonnées** dans `st.session_state`.
  Aligne la matrice avec la liste d’élèves courante.

* `app/data_statistics.py`
  Calculs : moyenne pondérée d’un élève, moyennes par trimestre (T1/T2/T3) et globale.
  Tolérance FR/EN sur les métadonnées.

* `app/data_visualization.py`
  Histogramme, boxplot, progression élève, moyenne de classe par évaluation et trimestre.
  Robuste aux données manquantes et colonnes FR/EN.

* `app/ui_components.py` (optionnel, mode legacy)
  Formulaire de saisie individuel (note/coefficient/trimestre) avec validations.

