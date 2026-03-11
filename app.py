from flask import Flask, request, jsonify
import smtplib
import random

app = Flask(__name__)

EMAIL = "yous01888@gmail.com"
PASSWORD = "jzip muri drsl kbej"

users = {}

@app.route("/signup", methods=["POST"])
def signup():

    data = request.json
    email = data["email"]
    password = data["password"]

    code = str(random.randint(100000,999999))

    users[email] = {
        "password":password,
        "code":code
    }

    message = f"Your verification code is: {code}"

    server = smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()
    server.login(EMAIL,PASSWORD)

    server.sendmail(
        EMAIL,
        email,
        message
    )

    server.quit()

    return jsonify({"message":"Verification code sent to Gmail"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
