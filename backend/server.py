import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from email.parser import BytesParser
from email.policy import default
import time
from datetime import datetime
import subprocess
import exifread

# Configurer le logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levellevel)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
MAX_FILE_AGE = 60

def delete_old_files():
    current_time = time.time()
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename == ".gitignore":
            continue
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getctime(file_path)
            if file_age > MAX_FILE_AGE:
                os.remove(file_path)
                logging.info(f"Supprimé : {file_path}")

delete_old_files()

FRONTEND_FOLDER = os.path.join(os.path.dirname(__file__), "../frontend")

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

def get_exif_tags(image_path):
    with open(image_path, 'rb') as image_file:
        tags = exifread.process_file(image_file, details=False)
    return tags

def calculate_confidence_level(tags, gps_metadata):
    confidence = 0

    # Vérifier si des métadonnées EXIF sont présentes
    if not tags:
        return confidence  # Retourner 0 si aucune métadonnée EXIF n'est trouvée

    # Vérifier la cohérence des dates et heures de prise de la photo
    if 'EXIF DateTimeOriginal' in tags and 'EXIF DateTimeDigitized' in tags:
        date_time_original = datetime.strptime(str(tags['EXIF DateTimeOriginal']), '%Y:%m:%d %H:%M:%S')
        date_time_digitized = datetime.strptime(str(tags['EXIF DateTimeDigitized']), '%Y:%m:%d %H:%M:%S')
        if date_time_original == date_time_digitized:
            confidence += 50  # Ajouter 50 points si les dates et heures sont cohérentes

    # Vérifier la géolocalisation
    if gps_metadata and gps_metadata.get('Latitude') != 0 and gps_metadata.get('Longitude') != 0:
        confidence += 50  # Ajouter 50 points si la géolocalisation est présente et valide

    return confidence

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            index_file_path = os.path.join(FRONTEND_FOLDER, "index.html")
            if os.path.exists(index_file_path):
                with open(index_file_path, "r", encoding="utf-8") as file:
                    self.wfile.write(file.read().encode('utf-8'))
            else:
                self.send_error(404, "Fichier index.html non trouvé dans le répertoire frontend")
        else:
            file_path = os.path.join(FRONTEND_FOLDER, self.path[1:])
            if os.path.exists(file_path):
                self.send_response(200)
                if self.path.endswith(".css"):
                    self.send_header("Content-type", "text/css")
                elif self.path.endswith(".js"):
                    self.send_header("Content-type", "application/javascript")
                elif self.path.endswith(".ico"):
                    self.send_header("Content-type", "image/x-icon")
                elif self.path.endswith(".jpg") or self.path.endswith(".jpeg") or self.path.endswith(".png"):
                    self.send_header("Content-type", "image/jpeg")
                self.end_headers()
                with open(file_path, "rb") as file:
                    self.wfile.write(file.read())
            else:
                self.send_error(404)
            return

        # Servir les fichiers du dossier uploads
        if self.path.startswith("/uploads/"):
            file_path = os.path.join(UPLOAD_FOLDER, self.path[len("/uploads/"):])
            logging.debug(f"Demande de fichier : {file_path}")
            if os.path.exists(file_path):
                self.send_response(200)
                if self.path.endswith(".jpg") or self.path.endswith(".jpeg") or self.path.endswith(".png"):
                    self.send_header("Content-type", "image/jpeg")
                self.end_headers()
                with open(file_path, "rb") as file:
                    self.wfile.write(file.read())
                logging.debug(f"Fichier servi : {file_path}")
            else:
                self.send_error(404, "Fichier non trouvé")
                logging.debug(f"Fichier non trouvé : {file_path}")
            return

    def do_POST(self):
        if self.path == "/":
            content_type = self.headers['Content-Type']
            if not content_type.startswith('multipart/form-data'):
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<h1>Erreur : Content-Type non supporté.</h1>".encode('utf-8'))
                return

            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            boundary = content_type.split("boundary=")[1].encode()
            parts = body.split(b"--" + boundary)

            for part in parts:
                if b"Content-Disposition" in part:
                    headers, file_data = part.split(b"\r\n\r\n", 1)
                    headers = headers.decode()
                    if 'filename="' in headers:
                        filename = headers.split('filename="')[1].split('"')[0]
                        file_path = os.path.join(UPLOAD_FOLDER, filename)

                        with open(file_path, 'wb') as f:
                            f.write(file_data.rstrip(b"\r\n--"))

                        logging.debug(f"Fichier téléchargé : {file_path}")

                        if os.listdir(UPLOAD_FOLDER):
                            # Exécuter le script app.py après le téléchargement du fichier
                            script_path = os.path.join(os.path.dirname(__file__), "app.py")
                            try:
                                logging.debug(f"Exécution du script : {script_path}")
                                result = subprocess.run(
                                    ["python", script_path],
                                    capture_output=True,
                                    text=True
                                )

                                logging.debug(f"Résultat stdout : {result.stdout}")
                                logging.debug(f"Résultat stderr : {result.stderr}")

                                # Vérification du fichier généré
                                html_file_path = "exif_metadata.html"
                                if os.path.exists(html_file_path):
                                    with open(html_file_path, "r", encoding="utf-8") as html_file:
                                        exif_metadata_content = html_file.read()
                                else:
                                    logging.error(f"Le fichier {html_file_path} n'a pas été généré.")
                                    exif_metadata_content = "<h2>Erreur : Le fichier exif_metadata.html est introuvable.</h2>"

                                # Lire les métadonnées EXIF et GPS
                                tags = get_exif_tags(file_path)
                                gps_metadata = get_gps_metadata(file_path)
                                if gps_metadata and gps_metadata.get('Latitude') != 0 and gps_metadata.get('Longitude') != 0:
                                    gps_info = f"<h2>Informations GPS :</h2><ul><li>Latitude: {gps_metadata.get('Latitude')}</li><li>Longitude: {gps_metadata.get('Longitude')}</li></ul>"
                                else:
                                    gps_info = f"<h2>Informations GPS :</h2><ul><li>Latitude: {gps_metadata.get('Latitude')}</li><li>Longitude: {gps_metadata.get('Longitude')}</li></ul><h2>Geolocalisation impossible</h2>"

                                # Calculer le niveau de confiance
                                confidence_level = calculate_confidence_level(tags, gps_metadata)

                                # Afficher la sortie du script, l'image téléchargée, les métadonnées GPS et le niveau de confiance
                                self.send_response(200)
                                self.send_header("Content-type", "text/html; charset=utf-8")
                                self.end_headers()
                                self.wfile.write(f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Upload réussi</title>
</head>
<body>
    <h2>Fichier téléchargé : {filename}</h2>
    <img src="/uploads/{filename}" alt="Image téléchargée" style="max-width: 100%; height: auto;">
    <h2>Résultat du script app.py :</h2>
    <pre>{result.stdout}</pre>
    <h2>Erreurs :</h2>
    <pre>{result.stderr}</pre>
    {exif_metadata_content}
    {gps_info}
    <h2>Niveau de confiance : {confidence_level}/100</h2>
</body>
</html>
""".encode('utf-8'))

                                logging.debug(f"Page HTML générée avec succès pour le fichier : {filename}")

                            except Exception as e:
                                logging.error(f"Erreur lors de l'exécution du script app.py : {e}")
                                self.send_response(500)
                                self.send_header("Content-type", "text/html; charset=utf-8")
                                self.end_headers()
                                self.wfile.write(f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Erreur</title>
</head>
<body>
    <h1>Erreur : Échec de l'exécution du script app.py</h1>
    <pre>{str(e)}</pre>
</body>
</html>
""".encode('utf-8'))
                        else:
                            self.send_response(500)
                            self.send_header("Content-type", "text/html; charset=utf-8")
                            self.end_headers()
                            self.wfile.write("""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Erreur</title>
</head>
<body>
    <h1>Erreur : Le dossier uploads est vide.</h1>
</body>
</html>
""".encode('utf-8'))
                            logging.debug("Le dossier uploads est vide.")
                        return

            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Erreur</title>
</head>
<body>
    <h1>Erreur : Aucun fichier sélectionné ou fichier invalide.</h1>
</body>
</html>
""".encode('utf-8'))
            logging.debug("Aucun fichier sélectionné ou fichier invalide.")

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Serveur démarré sur http://localhost:{port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()