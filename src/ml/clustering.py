import os
import re
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans

# --------------------------------------------------
# 1) Chargement des données
# --------------------------------------------------
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "hellowork2_preprocessed_ml.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "hellowork_with_clusters.csv")

df = pd.read_csv(INPUT_FILE)
print("Colonnes :", df.columns)
print(df.head())

# --------------------------------------------------
# 2) Construction de la colonne texte + nettoyage
# --------------------------------------------------
df["title_clean"] = df["title_clean"].fillna("")
df["description_clean"] = df["description_clean"].fillna("")
df["text_all"] = (df["title_clean"] + " " + df["description_clean"]).str.strip()

# Fonction de nettoyage : minuscule + suppression des chiffres
def clean_text(s: str) -> str:
    s = s.lower()
    # enlever les chiffres
    s = re.sub(r"\d+", " ", s)
    # enlever les multiples espaces
    s = re.sub(r"\s+", " ", s).strip()
    return s

df["text_clean"] = df["text_all"].astype(str).apply(clean_text)

mask_has_text = df["text_clean"].str.len() > 0
df_text = df[mask_has_text].copy()

print(f"Nombre de lignes avec texte non vide : {len(df_text)} / {len(df)}")

# --------------------------------------------------
# 3) TF-IDF sur le texte nettoyé
# --------------------------------------------------
tfidf = TfidfVectorizer(
    max_features=30000,
    ngram_range=(1, 2),
    min_df=2
)

X_tfidf = tfidf.fit_transform(df_text["text_clean"])
print("Shape TF-IDF :", X_tfidf.shape)

# --------------------------------------------------
# 4) Réduction de dimension
# --------------------------------------------------
svd = TruncatedSVD(
    n_components=200,
    random_state=42
)
X_reduced = svd.fit_transform(X_tfidf)
print("Shape après SVD :", X_reduced.shape)

# --------------------------------------------------
# 5) Clustering KMeans
# --------------------------------------------------
k = 8  # tu peux changer ce nombre
kmeans = KMeans(
    n_clusters=k,
    random_state=42,
    n_init=10
)

clusters = kmeans.fit_predict(X_reduced)
df_text["cluster"] = clusters

# --------------------------------------------------
# 6) Réinjecter les clusters dans le dataframe complet
# --------------------------------------------------
df["cluster"] = -1   # pour les lignes sans texte exploitable
df.loc[mask_has_text, "cluster"] = df_text["cluster"]

# --------------------------------------------------
# 7) Sauvegarde du fichier enrichi
# --------------------------------------------------
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
print(f"Fichier avec clusters sauvegardé : {OUTPUT_FILE}")

# --------------------------------------------------
# 8) Top mots par cluster (facultatif)
# --------------------------------------------------
terms = np.array(tfidf.get_feature_names_out())
order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]

print("\nTop mots par cluster (après nettoyage des nombres) :")
for i in range(k):
    top_terms = terms[order_centroids[i, :15]]
    print(f"\nCluster {i}:")
    print(", ".join(top_terms))
