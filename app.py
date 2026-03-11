from flask import Flask, request, jsonify
import random
import smtplib
from flask_cors import CORS
import os  # Import os for Railway PORT

app = Flask(__name__)
CORS(app)

# Gmail App Email iyo Password
EMAIL = "yous01888@gmail.com"
PASSWORD = "jzip muri drsl kbej"  # Hubi App Password sax

# Users storage (dictionary)
users = {}

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data["email"]
    password = data["password"]

    code = str(random.randint(100000, 999999))

    users[email] = {
        "password": password,
        "code": code,
        "verified": False
    }

    try:
        message = f"Your verification code is: {code}"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, email, message)
        server.quit()
        return jsonify({"message": "Verification code sent to Gmail"})
    except Exception as e:
        return jsonify({"message": f"Email send failed: {str(e)}"})


# ---------------- VERIFY ----------------
@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    code = data["code"]

    for user in users:
        if users[user]["code"] == code:
            users[user]["verified"] = True
            return jsonify({"message": "Account verified"})

    return jsonify({"message": "Invalid code"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data["email"]
    password = data["password"]

    if email in users:
        if users[email]["password"] == password:
            if users[email]["verified"]:
                return jsonify({"success": True, "message": "Login successful"})
            else:
                return jsonify({"success": False, "message": "Verify your email first"})

    return jsonify({"success": False, "message": "Invalid login"})


# ---------------- DOWNLOAD ----------------
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data["url"]

    # Halkan waxaad gelin kartaa yt-dlp logic si video loo download gareeyo
    return jsonify({"video": url})


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))  # 3000 local, Railway automatic PORT
    app.run(host="0.0.0.0", port=port)
