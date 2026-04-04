from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

app = Flask(
    __name__,
    static_folder="static",
    template_folder="pages"
)

CORS(app)

@app.route("/")
def index():
    return send_from_directory("pages", "base.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

# ⭐ זה מה שהיה חסר — מגיש את קבצי ה‑HTML של ה‑SPA
@app.route("/pages/<path:filename>")
def pages(filename):
    return send_from_directory("pages", filename)

# דוגמה ל‑API
@app.route("/api/test")
def api_test():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
