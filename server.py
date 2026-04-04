from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os

app = Flask(
    __name__,
    static_folder="static",
    template_folder="pages"
)

CORS(app)

# ---------------------------
#  ROUTE ראשי – טוען את האתר
# ---------------------------
@app.route("/")
def index():
    return send_from_directory("pages", "base.html")


# ---------------------------
#  טעינת קבצי STATIC (CSS/JS)
# ---------------------------
@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ---------------------------
#  דוגמה ל־API (אם יש לך API)
# ---------------------------
@app.route("/api/test")
def api_test():
    return jsonify({"status": "ok"})


# ---------------------------
#  הפעלת השרת
# ---------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
