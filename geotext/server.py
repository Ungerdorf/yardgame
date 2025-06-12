import http.server
import socketserver
import json
import os
import cgi
from urllib.parse import urlparse

PORT = int(os.environ.get('PORT', 8080))
DATA_FILE = os.path.join(os.path.dirname(__file__), 'recordings.json')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/recordings':
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/recordings':
            self.send_error(404)
            return
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
        if ctype != 'multipart/form-data':
            self.send_error(400, 'Expected multipart/form-data')
            return
        pdict['boundary'] = bytes(pdict['boundary'], 'utf-8')
        pdict['CONTENT-LENGTH'] = int(self.headers.get('content-length'))
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={'REQUEST_METHOD': 'POST'},
                                keep_blank_values=True)
        user_id = form.getvalue('userId', 'unknown')
        latitude = float(form.getvalue('latitude', '0'))
        longitude = float(form.getvalue('longitude', '0'))
        text = form.getvalue('text', '')
        upload = form['audio'] if 'audio' in form else None
        file_path = ''
        if upload is not None and upload.filename:
            filename = os.path.basename(upload.filename)
            file_path = os.path.join('uploads', filename)
            with open(os.path.join(os.path.dirname(__file__), file_path), 'wb') as f:
                f.write(upload.file.read())
        # Load existing data
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        # Create new record
        record = {
            'recordingId': len(data) + 1,
            'userId': user_id,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': int(__import__('time').time() * 1000),
            'text': text,
            'filePath': file_path
        }
        data.append(record)
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}).encode())

with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f'Serving on port {PORT}')
    httpd.serve_forever()
