# src/api.py

from flask import Flask, request, jsonify
import cv2
import numpy as np
import detection  # Importa as funções do detection.py

app = Flask(__name__)

@app.route('/detect', methods=['POST'])
def detect():
    if 'image' not in request.files:
        return jsonify({"error": "Nenhuma imagem enviada"}), 400
    
    file = request.files['image']
    # Lê a imagem do arquivo enviado
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    detections = detection.detect_objects(img)
    return jsonify({"detections": detections})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
