import os
import glob

# Chemin du dossier
path = "uploads/"
absolute_path = os.path.abspath(path)
print(f"[DEBUG] Chemin absolu du dossier : {absolute_path}")

# Vérifier si le dossier existe
if not os.path.exists(path):
    print(f"[DEBUG] Le dossier {path} n'existe pas.")
else:
    print(f"[DEBUG] Le dossier {path} existe.")

# Vérifier les fichiers dans le dossier
all_files = os.listdir(path)
print(f"[DEBUG] Tous les fichiers dans le dossier : {all_files}")

# Récupérer les fichiers images
image_files = (
    glob.glob(path + "*.jpg") +
    glob.glob(path + "*.jpeg") +
    glob.glob(path + "*.png")
)
print(f"[DEBUG] Fichiers images détectés : {image_files}")

if image_files:
    print(f"[DEBUG] Fichier image détecté : {image_files[0]}")
else:
    print("[DEBUG] Aucun fichier image compatible trouvé.")
