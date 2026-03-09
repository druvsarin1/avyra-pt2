import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from agent.agent import run_extraction

load_dotenv()

app = Flask(__name__)
CORS(app)


@app.route("/api/extract", methods=["POST"])
def extract():
    data = request.json
    mrn = data.get("mrn", "").strip()
    study_context = data.get("study_context", "").strip()
    variables = [v.strip() for v in data.get("variables", []) if v.strip()]

    if not mrn or not study_context or not variables:
        return jsonify({"error": "Missing mrn, study_context, or variables"}), 400

    try:
        result = run_extraction(mrn, study_context, variables)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
