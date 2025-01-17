import os
import glob
from PIL import Image
import exifread
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.imagenet_utils import decode_predictions
from tensorflow.keras.preprocessing.image import img_to_array
from skimage.io import imread
import numpy as np
from tensorflow.image import resize
from tensorflow.keras.applications.efficientnet import preprocess_input
import base64
import flickrapi
import cv2
import requests

# Paramètres de l'API Flickr
api_key = '261be8e647c2c815285b36e961dea61c'  # Remplace par ta propre clé API
api_secret = '95a053a26c49ec1c'  # Remplace par ta propre clé secrète

# Initialiser l'API de Flickr
flickr = flickrapi.FlickrAPI(api_key, api_secret, format='parsed-json')

# Définir le répertoire actuel
current_directory = os.getcwd()

# Fonction de débogage
def debug(message):
    print(f"[DEBUG] {message}")

# Chemin du dossier contenant les images
path = os.path.join(current_directory, "uploads/")
os.makedirs("flickr_images", exist_ok=True)  # Créer le dossier Flickr si nécessaire

# Recherche des fichiers image
image_files = glob.glob(os.path.join(path, "*.jpg")) + \
              glob.glob(os.path.join(path, "*.jpeg")) + \
              glob.glob(os.path.join(path, "*.png"))

if image_files:
    image_path = image_files[0]  # Utiliser la première image trouvée
    try:
        with open(image_path, 'rb') as image_file:
            # Lire les métadonnées EXIF
            tags = exifread.process_file(image_file, details=False)

        # Prétraiter l'image pour EfficientNetB0
        image = imread(image_path)
        image_size = 224
        image_resized = resize(image, (image_size, image_size))
        x = preprocess_input(img_to_array(image_resized))
        x = np.expand_dims(x, axis=0)

        # Charger le modèle et prédire
        model = EfficientNetB0(weights="imagenet")
        y = model.predict(x)
        decoded = decode_predictions(y, top=5)  # Obtenir les 5 meilleures prédictions

        # Extraire les deux meilleures prédictions et enlever tout ce qui suit un underscore
        best_predictions = [label.split('_')[0] for (_, label, _) in decoded[0][:2]]

        # Rechercher sur Flickr avec les termes séparés par une virgule et un espace
        search_term = ", ".join(best_predictions)  # Ajouter un espace après la virgule
        print(f"Termes de recherche pour Flickr : {search_term}")


        # Effectuer la recherche sur Flickr
        photos = flickr.photos.search(text=search_term, per_page=10, page=1, sort='relevance')
        print(f"Réponse Flickr : {photos}")

        # Télécharger les images récupérées
        image_paths = []
        for photo in photos['photos']['photo']:
            photo_id = photo['id']
            url = flickr.photos.getSizes(photo_id=photo_id)['sizes']['size'][3]['source']  # Taille moyenne
            img_name = f"flickr_images/{photo_id}.jpg"
            img_data = requests.get(url).content
            with open(img_name, 'wb') as handler:
                handler.write(img_data)
            image_paths.append(img_name)

        # Comparer les images téléchargées
        orb = cv2.ORB_create()
        query_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        keypoints, descriptors = orb.detectAndCompute(query_image, None)

        index_params = dict(algorithm=6, table_number=6, key_size=12, multi_probe_level=1)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        best_match = None
        max_good_matches = 0
        for flickr_image_path in image_paths:
            flickr_image = cv2.imread(flickr_image_path, cv2.IMREAD_GRAYSCALE)
            if flickr_image is None:
                continue

            keypoints_flickr, descriptors_flickr = orb.detectAndCompute(flickr_image, None)
            matches = flann.knnMatch(descriptors, descriptors_flickr, k=2)

            good_matches = []
            for match in matches:
                if len(match) == 2:
                    m, n = match
                    if m.distance < 0.7 * n.distance:
                        good_matches.append(m)

            if len(good_matches) > max_good_matches:
                max_good_matches = len(good_matches)
                best_match = flickr_image_path

        # Générer le fichier HTML
        html_content = "<html><meta charset='utf-8'><head><title>Analyse Image</title></head><body>"
        html_content += f"<h1>Image analysée : {os.path.basename(image_path)}</h1>"
        html_content += f"<img src='{image_path}' alt='Image analysée' style='max-width:500px;height:auto;'>"
        html_content += "<h2>Prédictions du modèle</h2><ul>"
        for rank, (imagenet_id, label, score) in enumerate(decoded[0], start=1):
            html_content += f"<li>{rank}. <strong>{label}</strong> (Score: {score:.4f})</li>"
        html_content += "</ul>"

        if best_match:
            html_content += f"<h2>Meilleure correspondance Flickr</h2><img src='{best_match}' style='max-width:500px;height:auto;'>"
        else:
            html_content += "<h2>Aucune correspondance trouvée sur Flickr.</h2>"

        html_content += "</body></html>"

        with open("result.html", "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

        # Ouvrir automatiquement dans le navigateur
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath('result.html')}")


        print("Analyse terminée. Résultats enregistrés dans 'result.html'.")
    except Exception as e:
        print(f"Erreur : {e}")
else:
    print("Aucune image trouvée dans le dossier 'uploads'.")
