"""
Simple Flask ML backend for Label Studio, bypassing label-studio-ml's
buggy v1/v2 manager to serve YOLO predictions directly.
"""
import os
import logging
import io
import requests
from flask import Flask, request, jsonify
from model import YOLOMLBackend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLOMLBackend()
        _model.setup()
        logger.info("YOLO model initialized")
    return _model


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "model_dir": None, "v2": False})


@app.route("/setup", methods=["POST"])
def setup():
    get_model()
    return jsonify({"model_version": "yolo11n"})


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json or {}
        tasks = data.get("tasks", [])
        label_config = data.get("label_config", "")
        model = get_model()
        predictions = model.predict(tasks, context={"label_config": label_config})
        return jsonify({"results": predictions, "model_version": "yolo11n"})
    except Exception as e:
        logger.exception("Prediction failed")
        return jsonify({"detail": str(e), "status": 500}), 500


@app.route("/train", methods=["POST"])
def train():
    return jsonify({"job_id": "not_supported"})


@app.route("/webhook", methods=["POST"])
def webhook():
    return jsonify({"status": "ok"})


@app.route("/versions", methods=["GET"])
def versions():
    return jsonify({"versions": ["yolo11n"]})
