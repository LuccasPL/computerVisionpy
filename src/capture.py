import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines
from roi_manager import carregar_rois, verificar_roi
from db import criar_tabela, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# Lista de classes permitidas
allowed_classes = ["sports ball", "tennis racket"]

# Parâmetro para reduzir o tamanho das bounding boxes (se desejado)
scale_factor = 0.9

# Instancia o tracker Deep SORT com max_age ajustado para não manter o track por muito tempo
tracker = DeepSort(max_age=2,  # ou 3
                   n_init=3, 
                   nn_budget=100, 
                   override_track_class=None, 
                   embedder="mobilenet")


def get_center(box):
    x, y, w, h = box
    return (x + w/2, y + h/2)

def associate_detection_with_track(track_box, detections, allowed_class=None):
    """
    Associa track_box ([x1, y1, x2, y2]) a uma detecção do YOLO que tenha,
    opcionalmente, a mesma allowed_class e seja a mais próxima (menor distância entre centros).
    Retorna o dicionário da detecção ou None.
    """
    tx = (track_box[0] + track_box[2]) / 2
    ty = (track_box[1] + track_box[3]) / 2
    best_det = None
    best_dist = float('inf')
    for det in detections:
        if allowed_class is not None and det["class"] != allowed_class:
            continue
        x, y, w, h = det["box"]
        cx, cy = x + w/2, y + h/2
        dist = ((tx - cx)**2 + (ty - cy)**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_det = det
    return best_det

def main():
    criar_tabela()
    rois = carregar_rois("data/annotations/rois_live.json")
    if not rois:
        print("Nenhuma ROI carregada. Calibre as prateleiras antes de iniciar.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao acessar a webcam.")
        return

    detection_interval = 3.0  # Processa a cada 3 segundos
    last_detection_time = time.time()

    # Dicionários de estado para cada track_id:
    estado_objetos = {}    # track_id -> (prateleira, bounding_box)
    classe_objetos = {}    # track_id -> classe
    ultima_insercao = {}    # track_id -> (prateleira, bounding_box)

    prev_detections = []   # Para desenho (lista de tuplas: (box, class, track_id, prateleira))

    # Limiar de ciclos sem update para disparar evento de saída
    TIME_SINCE_UPDATE_THRESHOLD = 2

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Falha ao capturar frame!")
            break

        current_time = time.time()
        elapsed = current_time - last_detection_time
        curr_detections = []  # Detecções deste ciclo para desenho

        if elapsed >= detection_interval:
            preproc = preprocess_for_shelf_detection(frame)
            shelf_lines = detect_shelf_lines(preproc)
            objects = detect_objects(frame)
            objects = [obj for obj in objects if obj["class"] in allowed_classes]

            tracker_dets = []
            for obj in objects:
                x, y, w, h = obj["box"]
                conf = obj["confidence"]
                tracker_dets.append(([x, y, x+w, y+h], conf))
            # Manter tracker_dets como lista
            tracks = tracker.update_tracks(tracker_dets, frame=frame)

            current_ids = set()
            for track in tracks:
                if not track.is_confirmed():
                    continue
                track_id = track.track_id
                current_ids.add(track_id)
                bbox = track.to_ltrb()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = map(int, bbox)
                
                # Se já houver classe para o track, obrigue a essa classe
                allowed_cls = classe_objetos.get(track_id, None)
                associated_det = associate_detection_with_track(bbox, objects, allowed_class=allowed_cls)
                if associated_det is None:
                    continue
                x, y, w, h = associated_det["box"]
                obj_class = associated_det["class"]

                # Se não houver classe registrada ainda, defina agora
                if track_id not in classe_objetos:
                    classe_objetos[track_id] = obj_class
                else:
                    if classe_objetos[track_id] != obj_class:
                        print(f"Forçando saída do track {track_id}. O objeto era {classe_objetos[track_id]}, mas apareceu {obj_class}")
                        # 1) Dispara evento de saída para a classe antiga
                        prateleira_ant, _ = estado_objetos[track_id]
                        inserir_evento(track_id, classe_objetos[track_id], prateleira_ant, "saída")
                        # 2) Remove o track do estado
                        del estado_objetos[track_id]
                        del classe_objetos[track_id]
                        if track_id in ultima_insercao:
                            del ultima_insercao[track_id]
                        # 3) Força o track a sumir do Deep SORT
                        track.time_since_update = 999
                        continue


                adjusted_box = [x, y, w, h]  # Usa a caixa original do YOLO

                center = (x + w//2, y + h//2)
                in_roi, roi = verificar_roi(center, rois)
                prateleira_atual = f"Prateleira {roi['id']}" if in_roi else "Fora da prateleira"

                estado_anterior = estado_objetos.get(track_id)  # por ex.: ("Prateleira 2", (100, 150, 50, 60))
                novo_estado = (prateleira_atual, tuple(adjusted_box))

                if estado_anterior is None:
                    # Primeiro registro do objeto
                    if prateleira_atual != "Fora da prateleira":
                        inserir_evento(track_id, obj_class, prateleira_atual, "entrada")
                    else:
                        inserir_evento(track_id, obj_class, "Fora da prateleira", "não identificado")
                    inserir_deteccao(obj_class, track_id, adjusted_box, True, roi["y1"] if in_roi else 0)
                    estado_objetos[track_id] = novo_estado
                    ultima_insercao[track_id] = novo_estado
                else:
                    antiga_prat, antiga_box = estado_anterior
                    nova_prat, nova_box = novo_estado
                    
                    # Se a prateleira REALMENTE mudou
                    if antiga_prat != nova_prat:
                        # Só registra saída se a prateleira anterior não for "Fora da prateleira"
                        if antiga_prat != "Fora da prateleira":
                            inserir_evento(track_id, obj_class, antiga_prat, "saída")
                        # Só registra entrada se a nova prateleira não for "Fora da prateleira"
                        if nova_prat != "Fora da prateleira":
                            inserir_evento(track_id, obj_class, nova_prat, "entrada")
                    else:
                        # Caso a prateleira seja a MESMA, NÃO dispara saída/entrada
                        # Apenas inserimos a detecção se a bounding box mudou significativamente
                        pass  # ou continue para não inserir nada
                    
                    # Se quiser registrar a mudança de bounding box na tabela de Detecoes,
                    # mas sem gerar saída/entrada, faça:
                    if nova_box != antiga_box:
                        inserir_deteccao(obj_class, track_id, adjusted_box, True, roi["y1"] if in_roi else 0)
                    
                    # Atualiza estado
                    estado_objetos[track_id] = novo_estado
                    ultima_insercao[track_id] = novo_estado


                curr_detections.append((adjusted_box, obj_class, track_id, prateleira_atual))

            last_detection_time = current_time

            # Verifica se algum track ficou sem atualização pelo tempo definido
            for track in tracks:
                if not track.is_confirmed():
                    continue
                if track.time_since_update >= TIME_SINCE_UPDATE_THRESHOLD:
                    tid = track.track_id
                    if tid in estado_objetos:
                        prateleira_ant, _ = estado_objetos[tid]
                        inserir_evento(tid, classe_objetos.get(tid, "unknown"), prateleira_ant, "saída")
                        del estado_objetos[tid]
                    if tid in classe_objetos:
                        del classe_objetos[tid]
                    if tid in ultima_insercao:
                        del ultima_insercao[tid]

            prev_detections = curr_detections.copy()

        # Desenha as detecções persistentes (dos ciclos anteriores) no frame
        for (box, obj_class, track_id, prateleira) in prev_detections:
            x, y, w, h = box
            color = (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            # Se desejar exibir rótulos, descomente:
            # cv2.putText(frame, f"{obj_class} (ID {track_id}) - {prateleira}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Desenha as ROIs
        for roi in rois:
            rx1, ry1, rx2, ry2 = roi["x1"], roi["y1"], roi["x2"], roi["y2"]
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255,255,0), 2)
            cv2.putText(frame, f"Prateleira {roi.get('id','')}", (rx1, ry1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 2)
        
        cv2.imshow("Deteccao e Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
