from flask import Flask, request, send_file, jsonify
import yt_dlp
import os

app = Flask(__name__)

# create folder safely
os.makedirs("downloads", exist_ok=True)

@app.route("/download", methods=["POST"])
def download():

    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "No URL provided"})

    ydl_opts = {
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
