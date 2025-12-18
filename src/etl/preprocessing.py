import pandas as pd
import numpy as np
import re

# ============================================================================
# CONFIG
# ============================================================================

INPUT_FILE = "data/hellowork_STRUCTURED_20251217_155217.csv"
OUTPUT_FILE = "data/hellowork_preprocessed_final.csv"

print(">>> ETL HELLOWORK – VERSION STRUCTURED <<<")

# ============================================================================
# 1️⃣ CHARGEMENT & ANALYSE
# ============================================================================

df = pd.read_csv(INPUT_FILE, encoding="utf-8")

print(f"✓ Dataset chargé : {df.shape[0]} lignes × {df.shape[1]} colonnes")

# ============================================================================
# 2️⃣ SUPPRESSION DES COLONNES INUTILES / TROP VIDES
# ============================================================================

# Colonnes inutiles connues (à ajuster si besoin)
DROP_COLS = [
    "Lien logo", "Logo", "ID", "Source",
    "Unnamed: 0"
]

df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)

# Suppression colonnes très vides (>70%)
threshold = 0.7
df = df.loc[:, df.isna().mean() < threshold]

print(f"✓ Colonnes après nettoyage : {df.shape[1]}")

# ============================================================================
# 3️⃣ NETTOYAGE TEXTE (SAFE POUR ML)
# ============================================================================

def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\-]", " ", text)
    return text.strip()

TEXT_COLS = ["titre", "description", "company"]

for col in TEXT_COLS:
    if col in df.columns:
        df[col] = df[col].fillna("")
        df[f"{col}_clean"] = df[col].apply(clean_text)

print("✓ Textes nettoyés")

# ============================================================================
# 4️⃣ TRAITEMENT DU SALAIRE (COMME AVANT)
# ============================================================================

# ============================================================================
# TRAITEMENT DU SALAIRE (COLONNE = "salaire")
# ============================================================================

def parse_salary(s):
    if pd.isna(s):
        return np.nan, np.nan

    s = str(s).lower()

    # Extraction des nombres
    nums = re.findall(r"\d+\.?\d*", s)
    if not nums:
        return np.nan, np.nan

    nums = [float(n) for n in nums]

    # Min / Max
    if len(nums) == 1:
        sal_min = sal_max = nums[0]
    else:
        sal_min, sal_max = min(nums[:2]), max(nums[:2])

    # Conversion en annuel
    if "heure" in s or "/h" in s:
        sal_min *= 35 * 47
        sal_max *= 35 * 47
    elif "mois" in s:
        sal_min *= 12
        sal_max *= 12

    return round(sal_min), round(sal_max)

# ⚠️ COLONNE CORRECTE : "salaire"
df[["salary_min", "salary_max"]] = df["salaire"].apply(
    lambda x: pd.Series(parse_salary(x))
)

df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

print(f"✓ Salaires traités : {df['salary_avg'].notna().sum()} offres")


# ============================================================================
# 5️⃣ REMOTE → VARIABLE BINAIRE
# ============================================================================

def detect_remote(row):
    text = ""
    for col in ["titre_clean", "description_clean"]:
        if col in row:
            text += " " + str(row[col])
    return int(bool(re.search(r"télétravail|remote|distanciel|hybride", text)))

df["remote"] = df.apply(detect_remote, axis=1)

print(f"✓ Remote détecté : {df['remote'].sum()} offres")

# ============================================================================
# 6️⃣ EXPÉRIENCE → ANNÉES NUMÉRIQUES
# ============================================================================

def parse_experience(exp):
    if pd.isna(exp):
        return np.nan

    exp = str(exp).lower()

    # Débutant
    if "débutant" in exp:
        return 0

    # X à Y ans
    m = re.search(r"(\d+)\s*à\s*(\d+)\s*an", exp)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2

    # X ans
    m = re.search(r"(\d+)\s*an", exp)
    if m:
        return int(m.group(1))

    return np.nan

df["experience_years"] = df["experience"].apply(parse_experience)

print(f"✓ Expérience numérique : {df['experience_years'].notna().sum()} offres")

# ============================================================================
# 7️⃣ NETTOYAGE FINAL
# ============================================================================

df["ville"] = df["ville"].fillna("Non précisé")
df["departement"] = df["departement"].fillna("Non précisé")
df["company"] = df["company"].fillna("Entreprise confidentielle")

# ============================================================================
# 8️⃣ EXPORT FINAL
# ============================================================================

df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("✅ ETL TERMINÉ")
print(f"📁 Fichier généré : {OUTPUT_FILE}")
