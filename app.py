
from flask import Flask, jsonify
from db import get_db_connection

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "message": "RampCoreOs API is running"
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
