from flask import Flask, request, send_file, render_template, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

# create downloads folder
os.makedirs("downloads", exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():

    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "No URL provided"})

    filename = f"downloads/{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": filename,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
