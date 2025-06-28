import os
import json
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

# ─── CONFIG ─────────────────────────────────────────────────────
IMAGE_SIZE = (790, 875)
STATIC_PATH = 'static'
LAYER_ORDER = [
    'background',
    'accessories2',   # ← new behind bodies, in front of background
    'bodies',
    'eyes',
    'mouth',
    'shirts',
    'hairs',
    'earrings',
    'toys',
    'accessories',
    'health',         # ← overlays everything at 30% opacity
]
# ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    # Gather PNGs per layer
    layer_files = {}
    for layer in LAYER_ORDER:
        folder = os.path.join(STATIC_PATH, layer)
        try:
            files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
        except FileNotFoundError:
            files = []
        layer_files[layer] = files

    return render_template(
        'index.html',
        layers=LAYER_ORDER,
        layer_files=layer_files,
        image_size=IMAGE_SIZE
    )

@app.route('/traits')
def traits():
    # Load report.json from the static folder
    report_path = os.path.join(STATIC_PATH, 'report.json')
    try:
        with open(report_path, 'r') as f:
            report_data = json.load(f)
    except FileNotFoundError:
        report_data = {"traits": {}, "error": "report.json not found"}
    except json.JSONDecodeError:
        report_data = {"traits": {}, "error": "Invalid JSON in report.json"}

    return render_template(
        'test.html',
        report=report_data
    )

# Serve static files
@app.route('/static/<path:path>')
def static_proxy(path):
    return send_from_directory(STATIC_PATH, path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')