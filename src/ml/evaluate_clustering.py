import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# ================================================
# 1. 📥 CHARGEMENT DU FICHIER CLUSTERED
# ================================================
df = pd.read_csv(r"C:\Users\malee\OneDrive\Dokumente\hellowork_BI\data\offres_clustered.csv")

# Colonnes utilisées pour le clustering
features = [
    "salary_min",
    "salary_max",
    "nb_skills",
    "days_since_publication",
    "urgent",
    "remote_possible",
    "contract_encoded",
    "studies_encoded",
    "experience_encoded"
]

df_features = df[features].copy()

# Sécurisation des NaN
df_features = df_features.fillna(df_features.median())

# Scaling
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_features)

# ================================================
# 2. ⭐ SILHOUETTE SCORE
# ================================================
try:
    sil_score = silhouette_score(X_scaled, df["cluster"])
    print("\n===== SILHOUETTE SCORE =====")
    print("Silhouette Score :", sil_score)

except Exception as e:
    print("Erreur Silhouette Score :", e)


# ================================================
# 3. 📉 MÉTHODE DU COUDE (ELBOW)
# ================================================
print("\n===== ELBOW METHOD =====")

inertia = []
K_range = range(2, 12)

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42)
    km.fit(X_scaled)
    inertia.append(km.inertia_)

plt.figure(figsize=(7,4))
plt.plot(K_range, inertia, marker="o")
plt.xlabel("Nombre de clusters (k)")
plt.ylabel("Inertie")
plt.title("Méthode du coude")
plt.grid(True)
plt.show()


# ================================================
# 4. 🎨 VISUALISATION PCA
# ================================================
print("\n===== VISUALISATION PCA =====")

pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

plt.figure(figsize=(7,5))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=df["cluster"], s=10)
plt.title("Projection PCA des clusters")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.colorbar(label="Cluster")
plt.show()


# ================================================
# 5. 📊 ANALYSE DES CENTROIDES
# ================================================
print("\n===== ANALYSE DES CLUSTERS =====")

cluster_summary = df.groupby("cluster")[features].mean()

print("\nCentroides des clusters :\n")
print(cluster_summary)
