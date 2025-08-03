import http.server
import socketserver
import json
import os
import cgi
from urllib.parse import urlparse
from math import radians, sin, cos, asin, sqrt

PORT = int(os.environ.get('PORT', 8080))
DATA_FILE = os.path.join(os.path.dirname(__file__), 'recordings.json')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)


def distance_m(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points."""
    r = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * r * asin(sqrt(a))


def load_data():
    """Load recording threads from disk and migrate old format if needed."""
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    if data and "threadId" not in data[0]:
        new = []
        for rec in data:
            thread = {
                "threadId": rec.get("recordingId"),
                "userId": rec.get("userId", "unknown"),
                "latitude": rec.get("latitude", 0),
                "longitude": rec.get("longitude", 0),
                "timestamp": rec.get("timestamp", 0),
                "text": rec.get("text", ""),
                "filePath": rec.get("filePath", ""),
                "aliases": {rec.get("userId", "unknown"): "@op"},
                "nextAlias": 1,
                "comments": [],
            }
            new.append(thread)
        data = new
        save_data(data)
    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

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
            data = load_data()
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
        thread_id_val = form.getvalue('threadId')
        thread_id = int(thread_id_val) if thread_id_val else None
        upload = form['audio'] if 'audio' in form else None
        file_path = ''
        if upload is not None and upload.filename:
            filename = os.path.basename(upload.filename)
            file_path = os.path.join('uploads', filename)
            with open(os.path.join(os.path.dirname(__file__), file_path), 'wb') as f:
                f.write(upload.file.read())
        # Load existing data
        data = load_data()
        now = int(__import__('time').time() * 1000)

        target_thread = None
        if thread_id:
            for th in data:
                if th.get('threadId') == thread_id:
                    target_thread = th
                    break
        if target_thread is None:
            # find nearby thread within 200m
            for th in data:
                dist = distance_m(latitude, longitude, th['latitude'], th['longitude'])
                if dist < 200:
                    target_thread = th
                    break

        if target_thread is None:
            # create new thread
            new_thread_id = (max([t['threadId'] for t in data]) + 1) if data else 1
            target_thread = {
                'threadId': new_thread_id,
                'userId': user_id,
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': now,
                'text': text,
                'filePath': file_path,
                'aliases': {user_id: '@op'},
                'nextAlias': 1,
                'comments': []
            }
            data.append(target_thread)
            save_data(data)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'threadId': new_thread_id}).encode())
            return

        # add comment to existing thread
        if 'aliases' not in target_thread:
            target_thread['aliases'] = {target_thread['userId']: '@op'}
            target_thread['nextAlias'] = 1
            target_thread.setdefault('comments', [])

        if user_id not in target_thread['aliases']:
            alias = f"@{target_thread['nextAlias']}"
            target_thread['aliases'][user_id] = alias
            target_thread['nextAlias'] += 1
        else:
            alias = target_thread['aliases'][user_id]

        comment = {
            'commentId': len(target_thread['comments']) + 1,
            'userId': user_id,
            'text': text,
            'timestamp': now,
            'filePath': file_path
        }
        target_thread['comments'].append(comment)

        save_data(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'threadId': target_thread['threadId'], 'commentId': comment['commentId'], 'alias': alias}).encode())

with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f'Serving on port {PORT}')
    httpd.serve_forever()
