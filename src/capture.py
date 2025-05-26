import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines
from roi_manager import (
    carregar_prateleiras, carregar_posicoes,
    verificar_prateleira, verificar_posicao
)
from db import criar_tabelas, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# — CONFIGURAÇÕES —
allowed_classes    = ["sports ball", "tennis racket"]
tracker            = DeepSort(max_age=2, n_init=3, nn_budget=100,
                             override_track_class=None, embedder="mobilenet")
DETECTION_INTERVAL = 5.0   # segundos
MISSING_THRESHOLD  = 5     # ciclos sem ver → saída

# mapeamento DeepSORT → nosso ID
dsort2app    = {}
next_my_id   = 1

# estados persistentes
estado       = {}  # my_id → {'cls':str,'shelf_id':int,'pos_id':int}
pos_occupied = {}  # (shelf_id,pos_id) → my_id
missing      = {}  # my_id → contagem
prev_draw    = []  # lista de caixas a desenhar

def associate_detection_with_track(track_box, detections, allowed_class=None):
    tx = (track_box[0] + track_box[2]) / 2
    ty = (track_box[1] + track_box[3]) / 2
    best, bd = None, float('inf')
    for det in detections:
        if allowed_class and det['class'] != allowed_class:
            continue
        x,y,w,h = det['box']
        cx,cy = x + w/2, y + h/2
        d = np.hypot(tx - cx, ty - cy)
        if d < bd:
            bd, best = d, det
    return best

def main():
    global next_my_id, estado, pos_occupied, missing, prev_draw

    # garante tabelas no BD
    criar_tabelas()

    # carrega ROIs de prateleiras e posições
    prateleiras = carregar_prateleiras("data/annotations/rois_prateleiras.json")
    posicoes     = carregar_posicoes("data/annotations/rois_posicoes.json")
    if not prateleiras or not posicoes:
        print("Calibre prateleiras e posições primeiro.")
        return

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Falha ao abrir webcam.")
        return

    last_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        curr_draw = []

        # a cada intervalo executa detecção + tracking
        if now - last_time >= DETECTION_INTERVAL:
            last_time = now

            # pré-processa apenas para detectar linhas de prateleiras
            pre = preprocess_for_shelf_detection(frame)
            _   = detect_shelf_lines(pre)

            # detecta todos os objetos de interesse no frame original
            dets_yolo = [o for o in detect_objects(frame) if o['class'] in allowed_classes]
            ds_inputs = [([x, y, x+w, y+h], o['confidence'])
                         for o in dets_yolo for x,y,w,h in [o['box']]]
            tracks    = tracker.update_tracks(ds_inputs, frame=frame)

            current_mids = set()

            for tr in tracks:
                if not tr.is_confirmed():
                    continue

                iid = tr.track_id
                # atribui nosso my_id persistente
                if iid not in dsort2app:
                    dsort2app[iid] = next_my_id
                    next_my_id += 1
                mid = dsort2app[iid]
                current_mids.add(mid)
                missing[mid] = 0

                # associa classe + bbox do YOLO
                bbox4 = tr.to_ltrb()
                det = associate_detection_with_track(bbox4, dets_yolo, estado.get(mid, {}).get('cls'))
                if not det:
                    continue
                x,y,w,h = det['box']
                cls     = det['class']

                # fixa classe na primeira vez
                if mid not in estado:
                    estado[mid] = {}
                if 'cls' not in estado[mid]:
                    estado[mid]['cls'] = cls

                # determina prateleira e posição
                cx, cy = x + w/2, y + h/2
                ok_shelf, shelf_roi = verificar_prateleira((cx,cy), prateleiras)
                shelf_id = shelf_roi['id'] if ok_shelf else None
                ok_pos, pos_roi = verificar_posicao((cx,cy), posicoes)
                pos_id   = pos_roi['pos_id'] if ok_pos else None

                # primeira aparição nessa posição: só entra se posição válida e livre
                if 'pos_id' not in estado[mid]:
                    if shelf_id is not None and pos_id is not None and (shelf_id, pos_id) not in pos_occupied:
                        inserir_evento(mid, cls, f"Prateleira {shelf_id}", f"Posição {pos_id}", "entrada")
                        inserir_deteccao(cls, mid, (x,y,w,h), True, None)
                        estado[mid]['shelf_id'] = shelf_id
                        estado[mid]['pos_id']   = pos_id
                        pos_occupied[(shelf_id,pos_id)] = mid
                        print(f"Objeto {cls} entrou: prateleira {shelf_id}, posição {pos_id}")
                    else:
                        # ignora detecção em posição inválida ou já ocupada
                        continue

                curr_draw.append(((x,y,w,h), cls, mid))

            # checa saídas por ausência
            for mid in list(estado):
                if mid not in current_mids:
                    missing[mid] += 1
                    if missing[mid] >= MISSING_THRESHOLD:
                        s_old = estado[mid]['shelf_id']
                        p_old = estado[mid]['pos_id']
                        c_old = estado[mid]['cls']
                        inserir_evento(mid, c_old, f"Prateleira {s_old}", f"Posição {p_old}", "saída")
                        # libera posição
                        pos_occupied.pop((s_old,p_old), None)
                        # limpa estado
                        del estado[mid]
                        del missing[mid]
                        # limpa mapping DeepSORT→my_id
                        for k,v in list(dsort2app.items()):
                            if v == mid:
                                del dsort2app[k]

            prev_draw = curr_draw

        # desenha os retângulos persistentes
        for (x,y,w,h), cls, mid in prev_draw:
            cv2.rectangle(frame, (int(x),int(y)), (int(x+w),int(y+h)), (0,255,0), 2)
            cv2.putText(frame, f"{cls} (ID {mid})", (int(x),int(y)-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        # desenha contornos de prateleiras e posições
        for r in prateleiras:
            cv2.rectangle(frame, (r['x1'],r['y1']), (r['x2'],r['y2']), (255,255,0), 1)
        for p in posicoes:
            cv2.rectangle(frame, (p['x1'],p['y1']), (p['x2'],p['y2']), (0,0,255), 1)

        cv2.imshow("Detecção e Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
