from flask import Flask, request, jsonify
import yt_dlp
import uuid
import os
import json

app = Flask(__name__)

HISTORY_FILE = "history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE,"r") as f:
        return json.load(f)

def save_history(data):
    with open(HISTORY_FILE,"w") as f:
        json.dump(data,f)

@app.route("/download",methods=["POST"])
def download():

    data = request.json
    url = data["url"]

    video_id = str(uuid.uuid4())
    filename = f"video_{video_id}.mp4"

    ydl_opts = {
        "format":"best",
        "outtmpl":filename
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    history = load_history()
    history.append({
        "url":url,
        "file":filename
    })
    save_history(history)

    return jsonify({
        "video":filename
    })

@app.route("/history")
def history():
    return jsonify(load_history())

app.run(host="0.0.0.0",port=3000)
