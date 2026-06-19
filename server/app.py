import os

from flask import Flask
from flask_cors import CORS

from pth_server import init_app_db, pth_bp

app = Flask(__name__)
CORS(app)

app.config["PTH_DB_PATH"] = os.environ.get("PTH_DB_PATH", "pth_data.db")
app.register_blueprint(pth_bp)
init_app_db(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
