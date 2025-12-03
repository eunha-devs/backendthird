import os
import discord
from discord.ext import commands
import threading
import asyncio
from flask import Flask, request, render_template, jsonify, send_from_directory
import sqlite3
import requests
from werkzeug.utils import secure_filename

# ============= Flask 앱 =============
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs('static/uploads', exist_ok=True)

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

@app.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    photo = request.files.get('photo')

    embed = {
        "title": "⚡ 새로운 DOX 도착 ⚡",
        "color": 16711680,
        "timestamp": request.headers.get('Date'),
        "fields": [],
        "footer": {"text": f"제출 IP: {request.remote_addr}"}
    }
    for k, v in data.items():
        if v.strip():
            embed["fields"].append({"name": k.replace('_', ' ').title(), "value": v[:1024]})

    files_to_send = None
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(path)
        photo_url = f"https://{request.host}/static/uploads/{filename}"
        embed["image"] = {"url": photo_url}

    # 모든 웹훅으로 즉시 전송
    conn = sqlite3.connect('doxbin.db')
    c = conn.cursor()
    c.execute("SELECT url FROM webhooks")
    for (url,) in c.fetchall():
        try:
            requests.post(url, json={"embeds": [embed]})
        except: pass
    conn.close()

    return jsonify({"status": "ㄷㄱㅈㅇ"})

# ============= 디스코드 봇 =============
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'봇 온라인: {bot.user}')

# 봇이 초대되면 자동으로 채널 만들고 웹훅 등록
@bot.event
async def on_guild_join(guild):
    channel = await guild.create_text_channel('doxbin-drop')
    webhook = await channel.create_webhook(name='Doxbin Auto')
    
    # 우리 Render 백엔드로 웹훅 자동 등록
    try:
        requests.post(f"https://{request.host}/register-webhook", 
                     json={"webhook": webhook.url}, timeout=5)
    except:
        pass
    
    await channel.send("```DOXBIN 자동 연결 완료```")

# 봇 토큰 (Render 환경변수로 넣을 거임)
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ← Render 대시보드에서 설정할 거

# ============= 동시에 돌리기 =============
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    bot.run(BOT_TOKEN)

if __name__ == '__main__':
    # Flask는 메인 스레드
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    run_flask()
