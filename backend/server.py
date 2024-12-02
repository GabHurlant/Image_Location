import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import time

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
MAX_FILE_AGE = 60

def delete_old_files():
    current_time = time.time()
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getctime(file_path)
            if file_age > MAX_FILE_AGE:
                os.remove(file_path)
                print(f"Supprimé : {file_path}")

# Appeler la fonction pour supprimer les fichiers vieux de plus de 1 minute
delete_old_files()

# Chemin vers le répertoire frontend où se trouve index.html
FRONTEND_FOLDER = "../frontend"  # Répertoire parent du dossier backend

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            # Envoie le formulaire HTML situé dans frontend/index.html
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Ouvre et envoie index.html depuis le répertoire frontend
            index_file_path = os.path.join(FRONTEND_FOLDER, "index.html")
            if os.path.exists(index_file_path):
                with open(index_file_path, "r") as file:
                    self.wfile.write(file.read().encode())
            else:
                self.send_error(404, "Fichier index.html non trouvé dans le répertoire frontend")
        else:
            # Serve static files
            file_path = os.path.join(FRONTEND_FOLDER, self.path[1:])
            if os.path.exists(file_path):
                self.send_response(200)
                if self.path.endswith(".css"):
                    self.send_header("Content-type", "text/css")
                elif self.path.endswith(".js"):
                    self.send_header("Content-type", "application/javascript")
                elif self.path.endswith(".ico"):
                    self.send_header("Content-type", "image/x-icon")
                self.end_headers()
                with open(file_path, "rb") as file:
                    self.wfile.write(file.read())
            else:
                self.send_error(404)

    def do_POST(self):
        if self.path == "/":
            # Lire la requête multipart/form-data
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})

            # Trouver la partie 'file'
            if "file" in form:
                file_field = form["file"]
                filename = file_field.filename
                file_data = file_field.file.read()

                # Sauvegarde le fichier dans le dossier uploads
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                with open(file_path, 'wb') as f:
                    f.write(file_data)

                # Réponse après le téléchargement, affichage sur la même page
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h1>Fichier {filename} téléchargé avec succès!</h1>".encode('utf-8'))
                return

            # Si aucun fichier n'a été trouvé
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h1>Erreur : Aucun fichier sélectionné ou fichier invalide.</h1>".encode('utf-8'))

# Configurer et démarrer le serveur
def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Serveur démarré sur http://localhost:{port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()
