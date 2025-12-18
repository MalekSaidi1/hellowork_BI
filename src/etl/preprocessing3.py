import pandas as pd
import numpy as np
import re
import os

# ===============================
# PATHS
# ===============================
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "hellowork_categories_20251216_104635.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "hellowork2_preprocessed_ml.csv")

# ===============================
# LOAD DATA
# ===============================
df = pd.read_csv(INPUT_FILE)

# ===============================
# TEXT CLEANING
# ===============================
def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"[^\w\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

df["title_clean"] = df["title"].apply(clean_text)
df["description_clean"] = df["short_description"].apply(clean_text)
df["company_clean"] = df["company"].fillna("Entreprise non précisée").apply(clean_text)



# ===============================
# LOCATION CLEANING (ROBUST)
# ===============================
def clean_location(loc):
    if pd.isna(loc):
        return "Non précisé", "Non précisé"

    loc = str(loc).lower().strip()

    # ❌ Cas évident de salaire
    if re.search(r"€|k|/mois|/heure|brut|net", loc):
        return "Non précisé", "Non précisé"

    # Cas : "75 - paris" ou "paris - 75"
    match_dash = re.search(r"(\d{1,2})\s*[-–]\s*([a-zÀ-ÿ\s\-]+)", loc)
    if match_dash:
        dept, city = match_dash.group(1), match_dash.group(2)
        return city.title().strip(), dept.zfill(2)

    match_dash_reverse = re.search(r"([a-zÀ-ÿ\s\-]+)\s*[-–]\s*(\d{1,2})", loc)
    if match_dash_reverse:
        city, dept = match_dash_reverse.group(1), match_dash_reverse.group(2)
        return city.title().strip(), dept.zfill(2)

    # Cas : "paris (75)"
    match_parentheses = re.search(r"([a-zÀ-ÿ\s\-]+)\s*\((\d{1,2})\)", loc)
    if match_parentheses:
        city, dept = match_parentheses.group(1), match_parentheses.group(2)
        return city.title().strip(), dept.zfill(2)

    # Cas : ville seule
    if re.fullmatch(r"[a-zÀ-ÿ\s\-]+", loc):
        return loc.title().strip(), "Non précisé"

    return "Non précisé", "Non précisé"


# ===============================
# SALARY PARSING (ANNUAL)
# ===============================
def parse_salary(s):
    if pd.isna(s):
        return np.nan, np.nan, None

    s = str(s).lower()

    is_hourly = "heure" in s
    is_monthly = "mois" in s

    s = re.sub(r"(\d+),(\d+)", r"\1.\2", s)
    s = re.sub(r"[\s\xa0]", "", s)

    nums = re.findall(r"\d+\.?\d*", s)
    if not nums:
        return np.nan, np.nan, None

    nums = [float(n) for n in nums]

    if len(nums) == 1:
        sal_min = sal_max = nums[0]
    else:
        sal_min, sal_max = min(nums), max(nums)

    if is_hourly:
        sal_min *= 35 * 47
        sal_max *= 35 * 47
        unit = "hourly"
    elif is_monthly:
        sal_min *= 12
        sal_max *= 12
        unit = "monthly"
    else:
        unit = "annual"

    return round(sal_min), round(sal_max), unit

df[["salary_min", "salary_max", "salary_unit"]] = df["salary"].apply(
    lambda x: pd.Series(parse_salary(x))
)

df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

# ===============================
# EXPERIENCE → YEARS ONLY
# ===============================
def extract_experience_years(exp):
    if pd.isna(exp):
        return np.nan

    exp = str(exp).lower()

    match_range = re.search(r"(\d+)\s*à\s*(\d+)\s*an", exp)
    if match_range:
        return (int(match_range.group(1)) + int(match_range.group(2))) / 2

    match_single = re.search(r"(\d+)\s*an", exp)
    if match_single:
        return int(match_single.group(1))

    return np.nan

df["experience_years"] = df["experience"].apply(extract_experience_years)

# ===============================
# REMOTE (BOOLEAN → INT)
# ===============================
df["remote"] = df["remote"].astype(int)

# ===============================
# LOCATION (GARANTI)
# ===============================
df[["city", "department"]] = df["location"].apply(
    lambda x: pd.Series(clean_location(x))
)

# Vérification
print(df[["location", "city", "department"]].head())





print("\n[ TARGET ] Création de la variable cible : salary_category")

# ============================================================================
# 1️⃣ Sélection des salaires valides
# ============================================================================

salary_valid = df["salary_avg"].dropna()

print(f"✓ Offres avec salaire : {len(salary_valid)} / {len(df)} "
      f"({len(salary_valid)/len(df)*100:.1f}%)")

# Sécurité minimale
if len(salary_valid) < 50:
    raise ValueError("❌ Pas assez de données salaire pour créer une target fiable")

# ============================================================================
# 2️⃣ Calcul des seuils par quantiles (DATA-DRIVEN)
# ============================================================================

Q33 = salary_valid.quantile(0.33)
Q66 = salary_valid.quantile(0.66)

print(f"✓ Seuils calculés :")
print(f"   - Bas   ≤ {Q33:,.0f} €")
print(f"   - Moyen ≤ {Q66:,.0f} €")
print(f"   - Haut  > {Q66:,.0f} €")

# ============================================================================
# 3️⃣ Fonction de catégorisation
# ============================================================================

def build_salary_category(salary):
    if pd.isna(salary):
        return np.nan
    elif salary <= Q33:
        return "Bas"
    elif salary <= Q66:
        return "Moyen"
    else:
        return "Haut"

# ============================================================================
# 4️⃣ Création de la colonne target
# ============================================================================

df["salary_category"] = df["salary_avg"].apply(build_salary_category)

# ============================================================================
# 5️⃣ Vérifications statistiques (OBLIGATOIRES)
# ============================================================================

print("\n📊 Distribution de la target :")
dist = df["salary_category"].value_counts(dropna=False)

print(dist)

print("\n📊 Pourcentage :")
print((dist / dist.sum() * 100).round(1))

# ============================================================================
# 6️⃣ Dataset ML (sans fuite de données)
# ============================================================================

df_ml = df.dropna(subset=["salary_category"]).copy()

print(f"\n✓ Dataset ML prêt : {len(df_ml)} lignes")

# ============================================================================
# 7️⃣ Sécurité finale
# ============================================================================

assert df_ml["salary_category"].isna().sum() == 0, "❌ Target contient des NaN"
assert set(df_ml["salary_category"].unique()) == {"Bas", "Moyen", "Haut"}, \
       "❌ Classes incorrectes"

print("\n✅ Target salary_category créée avec succès")


# ===============================
# FINAL DATASET (ML READY)
# ===============================
df_ml = df[
    [
        "category",
        "title_clean",
        "description_clean",
        "company_clean",
        "contract_type",
        "city",
        "department",
        "remote",
        "experience_years",
        "salary_min",
        "salary_max",
        "salary_avg",
        "salary_unit",
        "salary_category"
    ]
]

df_ml.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("✅ Preprocessing terminé")
print(f"📤 Fichier généré : {OUTPUT_FILE}")
