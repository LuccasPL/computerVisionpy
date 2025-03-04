# src/dashboard.py
from flask import Flask, render_template, Response
import cv2
import numpy as np
from detection import detect_objects  # Função já existente para detecção de objetos
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned

app = Flask(__name__)

def generate_frames():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Pré-processa o frame para detectar as prateleiras
        preprocessed = preprocess_for_shelf_detection(frame)
        shelf_lines = detect_shelf_lines(preprocessed)

        # Detecta os objetos na imagem
        objects = detect_objects(frame)

        # Para cada objeto detectado, verifica o alinhamento com as prateleiras
        for obj in objects:
            box = obj["box"]
            aligned, _ = is_aligned(box, shelf_lines, tolerance=20)
            color = (0, 255, 0) if aligned else (0, 0, 255)
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"{obj['class']} - {'Alinhado' if aligned else 'Desalinhado'}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Opcional: Desenha as linhas das prateleiras detectadas
        if shelf_lines is not None:
            for rho, theta in shelf_lines:
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a)))
                pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a)))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
