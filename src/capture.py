import cv2
import time
import numpy as np
from detection       import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines
from roi_manager     import (
    carregar_prateleiras, carregar_posicoes,
    verificar_prateleira, verificar_posicao
)
from db              import criar_tabelas, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# — CONFIGURAÇÕES —
allowed_classes    = ["sports ball", "tennis racket"]
tracker            = DeepSort(max_age=2, n_init=3, nn_budget=100,
                             override_track_class=None, embedder="mobilenet")
DETECTION_INTERVAL = 3.0   # segundos
MISSING_THRESHOLD  = 5     # ciclos sem ver → saída

# mapeamento DeepSORT → nosso ID
dsort2app    = {}
next_my_id   = 1

# estados persistentes
estado       = {}  # my_id → {'shelf':str,'pos':str}
pos_occupied = {}  # pos_id → my_id
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

    # garante banco
    criar_tabelas()

    # carrega ROIs
    prateleiras = carregar_prateleiras()
    posicoes     = carregar_posicoes()
    if not prateleiras or not posicoes:
        print("Calibre prateleiras e posições primeiro.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Falha ao abrir webcam.")
        return

    last_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret: break
        now = time.time()
        curr_draw = []

        # a cada intervalo executa detecção e tracking
        if now - last_time >= DETECTION_INTERVAL:
            last_time = now

            pre = preprocess_for_shelf_detection(frame)
            _   = detect_shelf_lines(pre)

            dets_yolo = [o for o in detect_objects(frame) if o['class'] in allowed_classes]
            ds_inputs = [([x, y, x+w, y+h], o['confidence'])
                         for o in dets_yolo for x,y,w,h in [o['box']]]
            tracks    = tracker.update_tracks(ds_inputs, frame=frame)

            current_mids = set()

            for tr in tracks:
                if not tr.is_confirmed():
                    continue
                iid = tr.track_id
                # mapeia → my_id
                if iid not in dsort2app:
                    dsort2app[iid] = next_my_id
                    next_my_id += 1
                mid = dsort2app[iid]
                current_mids.add(mid)
                missing[mid] = 0

                # bbox e classe
                bbox4 = tr.to_ltrb()
                det   = associate_detection_with_track(bbox4, dets_yolo, estado.get(mid, {}).get('cls'))
                if not det:
                    continue
                x,y,w,h = det['box']
                cls     = det['class']

                # fixa classe (primeira vez)
                if mid not in estado:
                    estado[mid] = {}
                if 'cls' not in estado[mid]:
                    estado[mid]['cls'] = cls

                # determina shelf + pos
                cx, cy = x + w/2, y + h/2
                ok_shelf, pr = verificar_prateleira((cx,cy), prateleiras)
                shelf_name = f"Prateleira {pr['id']}" if ok_shelf else "Fora da prateleira"
                ok_pos, po = verificar_posicao((cx,cy), posicoes)
                pos_label  = f"Posição {po['id']}" if ok_pos else None

                # primeira aparição em pos
                if 'pos_id' not in estado[mid]:
                    # só entra se posição válida e livre
                    if ok_pos and po['id'] not in pos_occupied:
                        inserir_evento(mid, cls, shelf_name, pos_label, "entrada")
                        inserir_deteccao(cls, mid, (x,y,w,h), True, None)
                        print(f"O objeto {cls} está na {shelf_name} e {pos_label}")
                        estado[mid]['shelf'] = shelf_name
                        estado[mid]['pos_id'] = po['id']
                        pos_occupied[po['id']] = mid
                    else:
                        continue
                # adiciona ao desenho
                curr_draw.append(((x,y,w,h), cls, mid, shelf_name))

            # checa saídas por ausência
            for mid in list(estado.keys()):
                if mid not in current_mids:
                    missing[mid] += 1
                    if missing[mid] >= MISSING_THRESHOLD:
                        shelf_old = estado[mid]['shelf']
                        pos_old   = f"Posição {estado[mid]['pos_id']}"
                        cls_old   = estado[mid]['cls']
                        inserir_evento(mid, cls_old, shelf_old, pos_old, "saída")
                        # libera posição e limpa
                        pos_occupied.pop(estado[mid]['pos_id'], None)
                        del estado[mid]
                        del missing[mid]
                        # limpa mapping inverso
                        for k,v in list(dsort2app.items()):
                            if v == mid:
                                del dsort2app[k]

            prev_draw = curr_draw

        # desenha caixas persistentes
        for (x,y,w,h), cls, mid, shelf_name in prev_draw:
            cv2.rectangle(frame, (int(x),int(y)), (int(x+w),int(y+h)), (0,255,0), 2)
            cv2.putText(frame, f"{cls} (ID {mid})", (int(x),int(y)-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        # desenha prateleiras e posições
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
