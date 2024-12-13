import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from email.parser import BytesParser
from email.policy import default
import time
import subprocess

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
                print(f"Supprimé : {file_path}")

delete_old_files()

FRONTEND_FOLDER = os.path.join(os.path.dirname(__file__), "../frontend")

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
                self.end_headers()
                with open(file_path, "rb") as file:
                    self.wfile.write(file.read())
            else:
                self.send_error(404)

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
    <h1>Fichier {filename} téléchargé avec succès!</h1>
</body>
</html>
""".encode('utf-8'))
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

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Serveur démarré sur http://localhost:{port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()


# Chemin vers le script Python à exécuter
script_path = "/backend/app.py"
# Exécuter le script
result = subprocess.run(["python", script_path], capture_output=True, text=True)

# Afficher la sortie du script
print(result.stdout)
print(result.stderr)