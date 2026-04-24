# app.py
from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "PipelineIQ test app"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/ping-external")
def ping_external():
    # Uses requests library — good candidate for dependency-related failures
    try:
        r = requests.get("https://httpbin.org/status/200", timeout=2)
        return jsonify({"external_status": r.status_code})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
