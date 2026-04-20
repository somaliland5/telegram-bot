from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        url = request.form.get("url")

        if not url:
            return "No URL provided"

        filename = f"{uuid.uuid4()}.mp4"

        ydl_opts = {
            "outtmpl": filename,
            "format": "mp4",
            "noplaylist": True,
            "quiet": True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return send_file(filename, as_attachment=True)

        except Exception as e:
            return f"Error: {str(e)}"

        finally:
            # cleanup file
            if os.path.exists(filename):
                os.remove(filename)

    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
