# src/capture.py

import cv2
import os

def capture_images(output_dir="data/raw/", num_images=10):
    # Cria o diretório, se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(0)  # 0 indica a webcam padrão
    
    count = 0
    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            print("Falha na captura da imagem.")
            break
        
        # Exibe o frame capturado
        cv2.imshow("Captura", frame)
        
        # Salva a imagem no diretório
        image_path = os.path.join(output_dir, f"img_{count:03d}.jpg")
        cv2.imwrite(image_path, frame)
        print(f"Imagem {count} salva em {image_path}")
        count += 1
        
        # Pressione 'q' para sair antecipadamente
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_images()
