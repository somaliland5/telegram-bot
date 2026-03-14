from flask import Flask, render_template, request, send_file
import yt_dlp
import os

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def home():

    if request.method == "POST":

        url = request.form["url"]

        ydl_opts = {
            "outtmpl": "video.mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return send_file("video.mp4", as_attachment=True)

    return render_template("index.html")

app.run(host="0.0.0.0", port=5000)
