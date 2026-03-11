from flask import Flask, request, jsonify
import random
import smtplib
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# ---------------- GMAIL CONFIG ----------------
EMAIL = "yous01888@gmail.com"
PASSWORD = "eerm bykd pozt hqip"  # Ku beddel App Password-kaaga

# ---------------- USERS STORAGE ----------------
users = {}  # Simple dictionary, haddii aad rabto DB waad beddeli kartaa

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    # Generate 6-digit verification code
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
        return jsonify({"message": f"Email send failed: {str(e)}"}), 500

# ---------------- VERIFY ----------------
@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    code = data.get("code")

    for email, info in users.items():
        if info["code"] == code:
            info["verified"] = True
            return jsonify({"message": "Account verified"})
    return jsonify({"message": "Invalid code"}), 400

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if email in users:
        info = users[email]
        if info["password"] == password:
            if info["verified"]:
                return jsonify({"success": True, "message": "Login successful"})
            else:
                return jsonify({"success": False, "message": "Verify your email first"})
    return jsonify({"success": False, "message": "Invalid login"})

# ---------------- DOWNLOAD ----------------
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")

    # Halkan waxaad ku dari kartaa yt-dlp logic si video dhab ah loo download gareeyo
    # Tusaale ahaan hadda waxay soo celineysaa URL la siiyay
    return jsonify({"video": url})

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))  # Railway PORT automatic
    app.run(host="0.0.0.0", port=port)
