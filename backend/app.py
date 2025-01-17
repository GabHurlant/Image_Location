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
import flickrapi
import requests
import cv2
import webbrowser
from datetime import datetime

# Paramètres de l'API Flickr
api_key = '261be8e647c2c815285b36e961dea61c'
api_secret = '95a053a26c49ec1c'

# Initialiser l'API de Flickr
flickr = flickrapi.FlickrAPI(api_key, api_secret, format='parsed-json')

# Définir le répertoire actuel
current_directory = os.getcwd()

# Chemin du dossier contenant les images
path = os.path.join(current_directory, "uploads/")
os.makedirs("flickr_images", exist_ok=True)

# Supprimer toutes les images déjà présentes dans le dossier 'flickr_images'
def clear_flickr_images_directory():
    folder = "flickr_images"
    for file_path in glob.glob(os.path.join(folder, "*")):
        try:
            os.remove(file_path)
        except Exception:
            pass

clear_flickr_images_directory()

# Recherche des fichiers image
image_files = glob.glob(os.path.join(path, "*.jpg")) + \
              glob.glob(os.path.join(path, "*.jpeg")) + \
              glob.glob(os.path.join(path, "*.png"))

# Fonction pour extraire les métadonnées EXIF
def get_exif_tags(image_path):
    with open(image_path, 'rb') as image_file:
        return exifread.process_file(image_file, details=False)

# Fonction pour extraire les données GPS
def get_gps_metadata(image_path):
    with open(image_path, 'rb') as image_file:
        tags = exifread.process_file(image_file, details=False)
        gps_info = {}
        if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
            latitude = tags['GPS GPSLatitude']
            longitude = tags['GPS GPSLongitude']
            if latitude.values[0].num == 0 and longitude.values[0].num == 0:
                gps_info['Latitude'] = 0
                gps_info['Longitude'] = 0
            else:
                gps_info['Latitude'] = latitude
                gps_info['Longitude'] = longitude
        return gps_info

# Fonction pour extraire la date et l'heure de la prise de la photo
def get_photo_datetime(image_path):
    with open(image_path, 'rb') as image_file:
        tags = exifread.process_file(image_file, details=False)
        if 'EXIF DateTimeOriginal' in tags:
            return str(tags['EXIF DateTimeOriginal'])
        else:
            return "Date et heure non disponibles"

# Fonction pour calculer le niveau de confiance basé sur les métadonnées EXIF et GPS
def calculate_confidence_level(tags, gps_metadata):
    confidence = 0

    # Vérifier si des métadonnées EXIF sont présentes
    if not tags:
        return confidence

    # Vérifier la cohérence des dates et heures de prise de la photo
    if 'EXIF DateTimeOriginal' in tags and 'EXIF DateTimeDigitized' in tags:
        date_time_original = datetime.strptime(str(tags['EXIF DateTimeOriginal']), '%Y:%m:%d %H:%M:%S')
        date_time_digitized = datetime.strptime(str(tags['EXIF DateTimeDigitized']), '%Y:%m:%d %H:%M:%S')
        if date_time_original == date_time_digitized:
            confidence += 50 

    # Vérifier la géolocalisation
    if gps_metadata and gps_metadata.get('Latitude') != 0 and gps_metadata.get('Longitude') != 0:
        confidence += 50

    return confidence

if image_files:
    # Trouver le fichier le plus récemment modifié
    latest_file = max(image_files, key=os.path.getmtime)
    image_path = latest_file

    try:
        # Prétraiter l'image pour EfficientNetB0
        image = imread(image_path)
        image_size = 224
        image_resized = resize(image, (image_size, image_size))
        x = preprocess_input(img_to_array(image_resized))
        x = np.expand_dims(x, axis=0)

        # Charger le modèle et prédire
        model = EfficientNetB0(weights="imagenet")
        y = model.predict(x)
        decoded = decode_predictions(y, top=5)

        # Extraire les deux meilleures prédictions et enlever tout ce qui suit un underscore
        best_predictions = [label.split('_')[0] for (_, label, _) in decoded[0][:2]]

        # Rechercher sur Flickr avec les termes séparés par une virgule et un espace
        search_term = ", ".join(best_predictions)

        # Effectuer la recherche sur Flickr
        photos = flickr.photos.search(text=search_term, per_page=10, page=1, sort='relevance')

        # Télécharger les images récupérées
        image_paths = []
        for photo in photos['photos']['photo']:
            photo_id = photo['id']
            url = flickr.photos.getSizes(photo_id=photo_id)['sizes']['size'][3]['source']
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

        # Lire les métadonnées EXIF et GPS
        tags = get_exif_tags(image_path)
        gps_metadata = get_gps_metadata(image_path)
        photo_datetime = get_photo_datetime(image_path)
        if gps_metadata and gps_metadata.get('Latitude') != 0 and gps_metadata.get('Longitude') != 0:
            gps_info = f"<h2>Informations GPS :</h2><ul><li>Latitude: {gps_metadata.get('Latitude')}</li><li>Longitude: {gps_metadata.get('Longitude')}</li></ul>"
        else:
            gps_info = "<h2>Geolocalisation impossible</h2>"

        # Calculer le niveau de confiance
        confidence_level = calculate_confidence_level(tags, gps_metadata)

        # Générer le fichier HTML
        html_content = "<html><meta charset='utf-8'><head><title>Analyse Image</title>"
        html_content += "<link rel='stylesheet' href='../frontend/main.css'>"
        html_content += "</head><body>"
        html_content += f"<h1>Image analysée : {os.path.basename(image_path)}</h1>"
        html_content += f"<img src='uploads/{os.path.basename(image_path)}' style='max-width:350px;height:auto;'>"
        html_content += f"<h2>Date et heure de la photo : {photo_datetime}</h2>"
        html_content += gps_info
        html_content += f"<h2>Niveau de confiance : {confidence_level}/100</h2>"
        html_content += "<h2>Prédictions du modèle</h2><ul>"
        for rank, (imagenet_id, label, score) in enumerate(decoded[0], start=1):
            html_content += f"<li>{rank}. <strong>{label}</strong> (Score: {score:.4f})</li>"
        html_content += "</ul>"

        if best_match:
            html_content += f"<h2>Meilleure correspondance Flickr</h2><img src='{best_match}' style='max-width:350px;height:auto;'>"
        else:
            html_content += "<h2>Aucune correspondance trouvée sur Flickr.</h2>"
        html_content += "</body></html>"

        with open("result.html", "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

        webbrowser.open(f"file://{os.path.abspath('result.html')}")

    except Exception as e:
        pass 

else:
    pass
