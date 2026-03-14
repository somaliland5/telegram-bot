from flask import Flask, render_template, request, send_file
import yt_dlp
import os

app = Flask(__name__)

DOWNLOAD_FILE = "video.mp4"

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        url = request.form.get("url")

        ydl_opts = {
            "outtmpl": DOWNLOAD_FILE,
            "format": "best"
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return send_file(DOWNLOAD_FILE, as_attachment=True)

        except Exception as e:
            return f"Error: {str(e)}"

    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
