import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned
from roi_manager import carregar_rois, verificar_roi
from db import criar_tabela, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# Instancia o tracker Deep SORT com os parâmetros desejados
tracker = DeepSort(max_age=30, n_init=3, nn_budget=100, override_track_class=None, embedder="mobilenet")

def get_center(box):
    # box: [x, y, w, h]
    x, y, w, h = box
    return (x + w/2, y + h/2)

def associate_detection_with_track(track_box, detections):
    """
    Associa o track_box (formato [x1, y1, x2, y2]) a uma das detecções originais,
    comparando a distância entre os centros.
    Retorna o dicionário de detecção correspondente.
    """
    tx = (track_box[0] + track_box[2]) / 2
    ty = (track_box[1] + track_box[3]) / 2
    best_det = None
    best_dist = float('inf')
    for det in detections:
        cx, cy = get_center(det["box"])
        dist = np.sqrt((tx - cx)**2 + (ty - cy)**2)
        if dist < best_dist:
            best_dist = dist
            best_det = det
    return best_det

def main():
    # Cria as tabelas necessárias no banco de dados
    criar_tabela()
    # Carrega as ROIs salvas (do calibracao_live.py)
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
            # Pré-processamento para detecção de prateleiras
            preprocessed = preprocess_for_shelf_detection(frame)
            shelf_lines = detect_shelf_lines(preprocessed)
            objects = detect_objects(frame)

            # Converter as detecções para o formato que o Deep SORT espera:
            # Uma lista onde cada elemento é: ([x1, y1, x2, y2], confidence)
            tracker_dets = []
            for obj in objects:
                x, y, w, h = obj["box"]
                conf = obj["confidence"]
                x1, y1 = x, y
                x2, y2 = x + w, y + h
                tracker_dets.append(([x1, y1, x2, y2], conf))
            
            # Atualiza o tracker com as detecções
            tracks = tracker.update_tracks(tracker_dets, frame=frame)
            last_detections = []

            # Para associar a detecção original (para obter a classe) com o tracker, use a função auxiliar
            for track in tracks:
                if not track.is_confirmed():
                    continue
                track_id = track.track_id
                bbox = track.to_ltrb()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = map(int, bbox)
                box = [x1, y1, x2 - x1, y2 - y1]
                # Associa a detecção original mais próxima ao track para obter a classe
                associated_det = associate_detection_with_track(bbox, objects)
                if associated_det is not None:
                    obj_class = associated_det["class"]
                else:
                    obj_class = "unknown"

                # Verifica o alinhamento (opcional)
                aligned, _ = is_aligned(box, shelf_lines)

                # Calcula o centro do objeto para verificar em qual ROI ele está
                center = (x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2)
                in_roi, roi = verificar_roi(center, rois)
                prateleira_atual = f"Prateleira {roi['id']}" if in_roi else "Fora da prateleira"

                # Registra eventos de entrada/saída
                estado_anterior = estado_objetos.get(track_id)
                if estado_anterior is None:
                    if in_roi:
                        inserir_evento(track_id, obj_class, prateleira_atual, "entrada")
                    else:
                        inserir_evento(track_id, obj_class, "N/A", "não identificado")
                else:
                    if estado_anterior != prateleira_atual:
                        if estado_anterior != "Fora da prateleira":
                            inserir_evento(track_id, obj_class, estado_anterior, "saída")
                        if in_roi:
                            inserir_evento(track_id, obj_class, prateleira_atual, "entrada")
                estado_objetos[track_id] = prateleira_atual

                last_detections.append((box, obj_class, track_id, aligned, prateleira_atual))
                x_disp, y_disp, w_disp, h_disp = box
                print(f"Objeto '{obj_class}' (ID {track_id}) -> (x={x_disp}, y={y_disp}, w={w_disp}, h={h_disp}) | {prateleira_atual} | Alinhado: {aligned}")
                inserir_deteccao(obj_class, int(track_id), box, aligned, roi["y1"] if in_roi else 0)
            
            last_detection_time = current_time

        # Desenha os resultados no frame
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
            cv2.putText(frame, f"Prateleira {roi.get('id', '')}", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 2)

        cv2.imshow("Deteccao com Registro de Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
