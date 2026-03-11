from flask import Flask, request, jsonify
import yt_dlp
import os

# Flask app samee
app = Flask(__name__)

@app.route("/")
def home():
    return "Downloader API Running"

@app.route("/download", methods=["POST"])
def download():

    data = request.json
    url = data["url"]

    ydl_opts = {
        "format": "best",
        "outtmpl": "video.%(ext)s"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    return jsonify({
        "video": filename
    })

port = int(os.environ.get("PORT",3000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
