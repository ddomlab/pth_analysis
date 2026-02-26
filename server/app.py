from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import pth_data

app = Flask(__name__)
CORS(app)

CSV_PATH = "pth_data.csv"


@app.route('/store_pth_data', methods=['POST'])
@cross_origin(origins="http://localhost:8000")
def store_pth_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    if pth_data.save_as_csv(CSV_PATH, data):
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500


@app.route('/pth/get_closest', methods=['GET'])
@cross_origin(origins="http://localhost:8000")
def get_closest_pth_data():
    target_time = request.args.get('time')
    if not target_time:
        return jsonify({"error": "No time provided"}), 400
    result = pth_data.get_closest_time(CSV_PATH, target_time)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "No matching data found"}), 404


@app.route("/api/pth/ndays", methods=["GET"])
def get_pth_data_ndays():
    """
    API endpoint to retrieve PTH data for the past N days.
    Example usage:
        /api/pth/ndays?days=3
    """
    days_arg = request.args.get("days", default="1")
    try:
        days = int(days_arg)
        if days <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": f"Invalid days parameter: {days_arg}"}), 400

    data = pth_data.get_recent_data(CSV_PATH, days)

    if data.empty:
        return jsonify([])

    data_dict = data.copy()
    data_dict['time'] = data_dict['time'].astype(int) // 10**9  # Convert to epoch seconds

    return jsonify(data_dict.to_dict('records'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)