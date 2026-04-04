from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

app = Flask(
    __name__,
    static_folder="static",
    template_folder="pages"
)

CORS(app)

# ---------------------------
#  דף הבית – טוען את base.html
# ---------------------------
@app.route("/")
def index():
    return send_from_directory("pages", "base.html")


# ---------------------------
#  טעינת קבצי STATIC (CSS/JS בלבד)
# ---------------------------
@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ---------------------------
#  דוגמה ל־API (אם יש צורך)
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
