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

# --- CONFIGURAÇÕES ---
allowed_classes    = ["sports ball", "tennis racket"]
tracker            = DeepSort(max_age=2, n_init=3, nn_budget=100,
                             override_track_class=None, embedder="mobilenet")
DETECTION_INTERVAL = 5.0  # segundos entre ciclos de detecção
MISSING_THRESHOLD  = 3    # ciclos sem ver => saída

# Map interno DeepSORT => nosso ID persistente
dsort2app = {}
next_my_id = 1

# Estados persistentes
estado       = {}      # my_id -> {'cls', 'shelf', 'pos_key'}
pos_occupied = set()   # set de (shelf_id, pos_id) ocupadas
missing      = {}      # my_id -> contagem de ciclos sem ver
prev_draw    = []      # rótulos a desenhar


def associate_detection_with_track(track_box, detections, forced_class=None):
    tx, ty = (track_box[0]+track_box[2]) / 2, (track_box[1]+track_box[3]) / 2
    best, bd = None, float('inf')
    for det in detections:
        if forced_class and det['class'] != forced_class:
            continue
        x, y, w, h = det['box']
        cx, cy = x + w/2, y + h/2
        d = np.hypot(tx - cx, ty - cy)
        if d < bd:
            bd, best = d, det
    return best


def main():
    global next_my_id, estado, pos_occupied, missing, prev_draw

    # inicializa banco de dados\    
    criar_tabelas()
    shelves  = carregar_prateleiras()
    posicoes = carregar_posicoes()
    if not shelves or not posicoes:
        print("Calibre prateleiras e posições antes.")
        return

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Falha ao abrir webcam.")
        return

    last = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        now = time.time()
        curr_draw = []

        # ciclo de detecção/tracking
        if now - last >= DETECTION_INTERVAL:
            last = now
            pre = preprocess_for_shelf_detection(frame)
            _   = detect_shelf_lines(pre)

            # YOLO detections + DeepSORT inputs
            dets_yolo = [o for o in detect_objects(frame) if o['class'] in allowed_classes]
            ds_inputs = [([x, y, x+w, y+h], o['confidence'])
                         for o in dets_yolo for x, y, w, h in [o['box']]]
            tracks = tracker.update_tracks(ds_inputs, frame=frame)

            current = set()
            for tr in tracks:
                if not tr.is_confirmed():
                    continue
                iid = tr.track_id
                # mapeia ID interno -> our ID
                if iid not in dsort2app:
                    dsort2app[iid] = next_my_id
                    next_my_id += 1
                mid = dsort2app[iid]
                current.add(mid)
                missing[mid] = 0

                # associa detecção YOLO ao track
                x1, y1, x2, y2 = map(int, tr.to_ltrb())
                det = associate_detection_with_track((x1, y1, x2, y2), dets_yolo, estado.get(mid, {}).get('cls'))
                if not det:
                    continue
                x, y, w, h = det['box']
                cls = det['class']

                # fixa classe no estado
                if mid not in estado:
                    estado[mid] = {}
                if 'cls' not in estado[mid]:
                    estado[mid]['cls'] = cls

                # determina prateleira
                cx, cy = x + w/2, y + h/2
                ok_s, s = verificar_prateleira((cx, cy), shelves)
                shelf_label = f"Prateleira {s['id']}" if ok_s else "Fora da prateleira"

                # determina posição
                ok_p, p = verificar_posicao((cx, cy), posicoes)
                if ok_p:
                    shelf_id = p['shelf_id']
                    pos_id   = p['pos_id']
                    pos_key  = (shelf_id, pos_id)
                else:
                    pos_key = None

                # primeira aparição em posição: só insere se livre
                if 'pos_key' not in estado[mid]:
                    if pos_key and pos_key not in pos_occupied:
                        inserir_evento(mid, cls, shelf_label, f"Posição {pos_id}", "entrada")
                        inserir_deteccao(cls, mid, (x, y, w, h), True, None)
                        estado[mid].update({'shelf': shelf_label, 'pos_key': pos_key})
                        pos_occupied.add(pos_key)
                    else:
                        continue

                # coleta para desenho persistente
                curr_draw.append(((x, y, w, h), cls, mid, shelf_label, pos_id))

            # detecta saída por ausência
            for mid in list(estado):
                if mid not in current:
                    missing[mid] += 1
                    if missing[mid] >= MISSING_THRESHOLD:
                        ent = estado[mid]
                        inserir_evento(mid, ent['cls'], ent['shelf'], f"Posição {ent['pos_key'][1]}", "saída")
                        pos_occupied.discard(ent['pos_key'])
                        del estado[mid]
                        del missing[mid]
                        # limpa mapeamento inverso
                        for k, v in list(dsort2app.items()):
                            if v == mid:
                                del dsort2app[k]
            prev_draw = curr_draw

        # desenho persistente
        for (x, y, w, h), cls, mid, shelf_label, pos_id in prev_draw:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{cls} (ID {mid})", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # desenha ROIs de prateleiras e posições
        for r in shelves:
            cv2.rectangle(frame, (r['x1'], r['y1']), (r['x2'], r['y2']), (255, 255, 0), 1)
        for p in posicoes:
            cv2.rectangle(frame, (p['x1'], p['y1']), (p['x2'], p['y2']), (0, 0, 255), 1)

        cv2.imshow("Detecção e Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
