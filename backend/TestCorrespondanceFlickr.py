import flickrapi
import cv2
import numpy as np
import requests
import os
import matplotlib.pyplot as plt

# Paramètres de l'API Flickr
api_key = '261be8e647c2c815285b36e961dea61c'  # Remplace par ta propre clé API
api_secret = '95a053a26c49ec1c'  # Remplace par ta propre clé secrète

# Initialiser l'API de Flickr
flickr = flickrapi.FlickrAPI(api_key, api_secret, format='parsed-json')

# Recherche des images sur Flickr pour le mot-clé 'fire' et triées par popularité
photos = flickr.photos.search(text='merle', per_page=10, page=1, sort='relevance')

# Créer un dossier pour sauvegarder les images téléchargées
os.makedirs('flickr_images', exist_ok=True)

# Télécharger les images récupérées de Flickr et les afficher
image_paths = []
for photo in photos['photos']['photo']:
    photo_id = photo['id']
    url = flickr.photos.getSizes(photo_id=photo_id)['sizes']['size'][3]['source']  # Taille moyenne

    # Télécharger l'image
    img_data = requests.get(url).content
    img_name = f"flickr_images/{photo_id}.jpg"
    with open(img_name, 'wb') as handler:
        handler.write(img_data)

    print(f"Téléchargé : {img_name}")
    image_paths.append(img_name)

# Afficher toutes les images téléchargées avec matplotlib
plt.figure(figsize=(10, 10))

# Afficher les images téléchargées
for i, image_path in enumerate(image_paths):
    img = cv2.imread(image_path)
    plt.subplot(2, 5, i + 1)  # Créer une grille de 2 lignes et 5 colonnes
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))  # Convertir BGR en RGB pour affichage
    plt.axis('off')  # Désactiver les axes pour une meilleure vue

plt.tight_layout()
plt.show()

# Charger l'image de requête (celle que tu veux comparer)
image_path = 'merle.jpg'  # Remplace par ton image de requête
image_resized = cv2.imread(image_path, cv2.IMREAD_COLOR)  # Charger en couleur

if image_resized is None:
    print(f"Erreur lors du chargement de l'image : {image_path}")
else:
    plt.imshow(cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB))  # Convertir BGR en RGB pour affichage
    plt.title("Image de départ")
    plt.show()

# Initialiser l'ORB detector
orb = cv2.ORB_create()

# Trouver les points clés et descripteurs pour l'image de requête
keypoints, descriptors = orb.detectAndCompute(image_resized, None)

# Initialiser le matcher FLANN
index_params = dict(algorithm=6, table_number=6, key_size=12, multi_probe_level=1)
search_params = dict(checks=50)
flann = cv2.FlannBasedMatcher(index_params, search_params)

# Comparer les images téléchargées depuis Flickr avec l'image de requête
flickr_folder = 'flickr_images'
best_match = None
max_good_matches = 0

# Comparer chaque image de la base Flickr avec l'image de requête
for flickr_image_path in os.listdir(flickr_folder):
    if flickr_image_path.endswith('.jpg'):
        # Charger l'image Flickr
        flickr_image = cv2.imread(os.path.join(flickr_folder, flickr_image_path), cv2.IMREAD_GRAYSCALE)

        if flickr_image is None:
            continue

        # Trouver les points clés et descripteurs pour l'image Flickr
        keypoints_flickr, descriptors_flickr = orb.detectAndCompute(flickr_image, None)

        # Trouver les correspondances entre les descripteurs de l'image de requête et de l'image Flickr
        matches = flann.knnMatch(descriptors, descriptors_flickr, k=2)

        # Appliquer le ratio test de Lowe
        good_matches = []
        for match in matches:
            if len(match) == 2:  # Vérifier qu'il y a bien 2 éléments à déballer
                m, n = match
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        # Garder la meilleure correspondance
        if len(good_matches) > max_good_matches:
            max_good_matches = len(good_matches)
            best_match = flickr_image_path

# Afficher la meilleure correspondance
if best_match:
    print(f"La meilleure correspondance est l'image : {best_match} avec {max_good_matches} bonnes correspondances")
    # Afficher l'image correspondante
    best_image = cv2.imread(os.path.join(flickr_folder, best_match))
    plt.imshow(cv2.cvtColor(best_image, cv2.COLOR_BGR2RGB))
    plt.title(f"Meilleure correspondance : {best_match}")
    plt.show()
else:
    print("Aucune correspondance trouvée.")
