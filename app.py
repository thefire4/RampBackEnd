
from flask import Flask, jsonify
from db import get_db_connection

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "message": "RampCoreOs API is running"
    })

@app.route("/api/health/db")
def database_health():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

        return jsonify({
            "status": "connected",
            "database": database_name
        })

    except Exception:
        app.logger.exception("Database connection failed")
        return jsonify({
            "status": "error",
            "message": "Unable to connect to the database"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
