import os
import glob
from PIL import Image
import exifread

current_directory = os.getcwd()
print(f"[DEBUG] Répertoire de travail actuel : {current_directory}")
# Fonction de débogage
def debug(message):
    print(f"[DEBUG] {message}")

# Chemin du dossier contenant les images
path = "backend/uploads/"

debug(f"Chemin défini : {path}")

image_files = glob.glob(os.path.join(path, "*.jpg")) + \
              glob.glob(os.path.join(path, "*.jpeg")) + \
              glob.glob(os.path.join(path, "*.png"))

debug(f"Fichiers trouvés : {image_files}")

# Vérifier s'il y a des fichiers image dans le dossier
if image_files:
    # Ouvrir le premier fichier image trouvé
    image_path = image_files[0]
    debug(f"Fichier sélectionné : {image_path}")
    
    try:
        with open(image_path, 'rb') as image_file:
            # Lire les métadonnées EXIF
            debug("Lecture des métadonnées EXIF en cours...")
            tags = exifread.process_file(image_file, details=False)
            debug(f"Nombre de tags EXIF trouvés : {len(tags)}")
            
            # Générer le contenu HTML
            html_content = "<html><head><title>Métadonnées EXIF</title></head><body>"
            html_content += f"<h1>Métadonnées EXIF pour : {os.path.basename(image_path)}</h1><ul>"
            
            if tags:
                for tag in tags.keys():
                    debug(f"Tag trouvé : {tag} = {tags[tag]}")
                    html_content += f"<li><strong>{tag}:</strong> {tags[tag]}</li>"
            else:
                debug("Aucune métadonnée EXIF trouvée.")
                html_content += "<li>Aucune métadonnée EXIF trouvée.</li>"
                
            html_content += "</ul></body></html>"
            
            # Écrire le contenu HTML dans un fichier
            debug("Écriture du contenu HTML dans 'exif_metadata.html'...")
            with open("exif_metadata.html", "w", encoding="utf-8") as html_file:
                html_file.write(html_content)
            
            debug("Les métadonnées EXIF ont été extraites avec succès.")
            print("Les métadonnées EXIF ont été enregistrées dans 'exif_metadata.html'.")
    except Exception as e:
        debug(f"Erreur lors du traitement de l'image : {e}")
        print(f"Une erreur s'est produite : {e}")
else:
    debug("Aucun fichier compatible trouvé dans le dossier.")
    print("Aucune image compatible trouvée dans le dossier.")
