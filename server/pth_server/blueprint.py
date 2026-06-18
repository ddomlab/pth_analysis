from flask import Blueprint, Flask, current_app, jsonify, request, send_from_directory

from . import pth_data

DEFAULT_DB_PATH = "pth_data.db"

pth_bp = Blueprint("pth", __name__, url_prefix="/pth", static_folder="static")


def init_app_db(app: Flask) -> None:
    """ Call once at startup, whether running standalone or mounted on an
    existing Flask app, to create the schema if it doesn't already exist. """
    db_path = app.config.setdefault("PTH_DB_PATH", DEFAULT_DB_PATH)
    pth_data.init_db(db_path)


def _db_path() -> str:
    return current_app.config.get("PTH_DB_PATH", DEFAULT_DB_PATH)


def _serialize_dataframe(data):
    if data.empty:
        return jsonify([])
    return jsonify(data.to_dict("records"))


@pth_bp.route("/dashboard")
def dashboard():
    return send_from_directory(pth_bp.static_folder, "pth_analysis.html")


@pth_bp.route("/api/store_data", methods=["POST"])
def store_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    if pth_data.save_reading(_db_path(), data):
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500


@pth_bp.route("/api/closest", methods=["GET"])
def closest():
    target_time = request.args.get("time")
    if not target_time:
        return jsonify({"error": "No time provided"}), 400
    result = pth_data.get_closest_reading(_db_path(), target_time)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "No matching data found"}), 404


@pth_bp.route("/api/ndays", methods=["GET"])
def ndays():
    """
    Returns PTH data for the past N days.
    Example usage:
        /pth/api/ndays?days=3
    """
    days_arg = request.args.get("days", default="1")
    try:
        days = int(days_arg)
        if days <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": f"Invalid days parameter: {days_arg}"}), 400

    return _serialize_dataframe(pth_data.get_recent_readings(_db_path(), days))


@pth_bp.route("/api/range", methods=["GET"])
def data_range():
    """
    Returns all PTH data points with a time between 'start' and 'end' (inclusive).
    Each accepts a Unix epoch integer or an ISO 8601 datetime string.
    Example usage:
        /pth/api/range?start=1740000000&end=2025-03-01T00:00:00
    """
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"error": "Both start and end are required"}), 400

    try:
        data = pth_data.get_readings_in_range(_db_path(), start, end)
    except ValueError:
        return jsonify({"error": f"Invalid start/end value: {start!r}, {end!r}"}), 400

    return _serialize_dataframe(data)
