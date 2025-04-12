# src/preprocess.py

import cv2
import os

def preprocess_image(input_path, output_path, target_size=(416, 416)):
    # Lê a imagem
    image = cv2.imread(input_path)
    if image is None:
        print(f"Erro ao ler a imagem {input_path}")
        return
    
    # Redimensiona a imagem para o tamanho alvo
    processed_image = cv2.resize(image, target_size)
    
    # (Opcional) Normalização: converte os valores dos pixels para [0, 1]
    processed_image = processed_image / 255.0
    
    # Salva a imagem pré-processada
    # Se necessário, converta de volta para formato [0,255] para salvamento visual
    save_image = (processed_image * 255).astype("uint8")
    cv2.imwrite(output_path, save_image)
    print(f"Imagem pré-processada salva em {output_path}")

if __name__ == "__main__":
    os.makedirs("data/processed/", exist_ok=True)
    input_img = "data/raw/img_009.jpg"  # Exemplo: imagem capturada anteriormente
    output_img = "data/processed/img_000_processed.jpg"
    preprocess_image(input_img, output_img)
