from flask import Flask, request, render_template, jsonify
import sqlite3
import requests
import os

app = Flask(__name__)

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
    return jsonify({"status": "invalid"}), 400

@app.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    files = request.files
    photo = files.get('photo')

    embed = {
        "title": "어떤 멍청한 새끼 하나 더 걸림!!! ㄹㅈㄷ!!!",
        "color": 16711680,
        "timestamp": request.headers.get('X-Now', None),
        "fields": [],
        "footer": {"text": f"제출자 IP: {request.remote_addr}"}
    }

    for key, value in data.items():
        if value.strip():
            embed["fields"].append({"name": key.replace('_', ' ').title(), "value": value[:1024], "inline": False})

    attachments = []
    if photo and photo.filename:
        photo_url = f"https://yourdomain.com/static/uploads/{photo.filename}"
        embed["image"] = {"url": photo_url}
        photo.save(os.path.join('static/uploads', photo.filename))
        attachments.append({"attachment": photo.read(), "name": photo.filename})
    conn = sqlite3.connect('doxbin.db')
    c = conn.cursor()
    c.execute("SELECT url FROM webhooks")
    webhooks = [row[0] for row in c.fetchall()]
    conn.close()

    for webhook_url in webhooks:
        try:
            requests.post(webhook_url, json={"embeds": [embed]}, files=attachments if attachments else None)
        except:
            pass

    return jsonify({"status": "dox delivered to all servers"})

if not os.path.exists('static/uploads'):
    os.makedirs('static/uploads')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
