import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned
from roi_manager import carregar_rois, verificar_roi
from db import criar_tabela, inserir_deteccao, inserir_evento  # Agora com inserir_evento

def main():
    # Cria as tabelas necessárias
    criar_tabela()  # Para Detecoes (já feito)
    # Certifique-se de que a tabela Eventos já foi criada (execute o comando SQL manualmente ou adicione a criação aqui)

    # Carrega as ROIs calibradas
    rois = carregar_rois("data/annotations/rois_live.json")
    if not rois:
        print("Nenhuma ROI carregada. Calibre as prateleiras antes de iniciar.")
    
    cap = cv2.VideoCapture(0)
    detection_interval = 5.0  # Detecção a cada 5 segundos
    last_detection_time = time.time()
    last_detections = []
    
    # Dicionário para manter o estado dos objetos (track_id: prateleira atual)
    estado_objetos = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        elapsed = current_time - last_detection_time

        if elapsed >= detection_interval:
            preprocessed = preprocess_for_shelf_detection(frame)
            shelf_lines = detect_shelf_lines(preprocessed)
            objects = detect_objects(frame)
            last_detections = []

            for obj in objects:
                box = obj["box"]  # [x, y, w, h]
                # Verificação de alinhamento (usando linhas de prateleiras)
                aligned, _ = is_aligned(box, shelf_lines)
                
                # Calcula o centro do objeto para determinar em qual ROI ele está
                x, y, w, h = box
                center = (x + w // 2, y + h // 2)
                in_roi, roi = verificar_roi(center, rois)
                prateleira_atual = f"Prateleira {roi['id']}" if in_roi else "Fora da prateleira"

                # Supondo que o tracker atribua um track_id
                track_id = obj.get("track_id", 0)
                
                # Verifica o estado anterior para esse objeto
                estado_anterior = estado_objetos.get(track_id)
                if estado_anterior is None:
                    # Se o objeto não tinha estado registrado, considere como entrada se estiver em uma prateleira
                    if in_roi:
                        inserir_evento(track_id, obj["class"], prateleira_atual, "entrada")
                    else:
                        inserir_evento(track_id, obj["class"], "N/A", "não identificado")
                else:
                    # Se o objeto já estava registrado e mudou de prateleira
                    if estado_anterior != prateleira_atual:
                        # Registra saída da prateleira antiga
                        if estado_anterior != "Fora da prateleira":
                            inserir_evento(track_id, obj["class"], estado_anterior, "saída")
                        # Registra entrada na nova prateleira, se aplicável
                        if in_roi:
                            inserir_evento(track_id, obj["class"], prateleira_atual, "entrada")
                
                # Atualiza o estado atual do objeto
                estado_objetos[track_id] = prateleira_atual

                # Armazena o resultado para exibição
                last_detections.append((box, obj["class"], track_id, aligned, prateleira_atual))
                print(f"Objeto '{obj['class']}' (ID {track_id}) -> (x={x}, y={y}, w={w}, h={h}) | {prateleira_atual} | Alinhado: {aligned}")
                inserir_deteccao(obj["class"], int(track_id), box, aligned, roi["y1"] if in_roi else 0)
            
            last_detection_time = current_time

        # Desenha as detecções e informações no frame
        for (box, obj_class, track_id, aligned, prateleira_atual) in last_detections:
            x, y, w, h = box
            color = (0, 255, 0) if aligned else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"{obj_class} (ID {track_id}) - {prateleira_atual}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Desenha as ROIs para visualização
        for roi in rois:
            x1, y1, x2, y2 = roi["x1"], roi["y1"], roi["x2"], roi["y2"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(frame, f"Prateleira {roi.get('id', '')}", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        cv2.imshow("Deteccao com Registro de Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
