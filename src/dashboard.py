# src/dashboard.py

from flask import Flask, render_template, Response
import cv2
import detection

app = Flask(__name__)

# Função para capturar o vídeo da webcam e aplicar a detecção
def generate_frames():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            detections = detection.detect_objects(frame)
            # Desenhar as caixas
            for det in detections:
                x, y, w, h = det["box"]
                label = det["class"]
                confidence = det["confidence"]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            # Renderiza o frame no formato multipart
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    # Renderiza o template HTML
    return render_template('dashboard.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
