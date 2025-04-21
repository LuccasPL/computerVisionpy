import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines
from roi_manager import carregar_rois
from db import criar_tabela, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# --- CONFIGURAÇÕES ---
allowed_classes = ["sports ball", "tennis racket"]
tracker = DeepSort(
    max_age=2,      # descarta tracks ausentes rapidamente
    n_init=3,
    nn_budget=100,
    override_track_class=None,
    embedder="mobilenet"
)
detection_interval = 5.0  # segundos entre detecções
MISSING_THRESHOLD = 2      # ciclos sem detecção para saída de evento

# --- MAPEAMENTO INTERNAL -> APP ID ---
# Cada internal track_id mapeia para um my_id único e persistente
# Removeremos o mapping apenas quando my_id for encerrado
# (i.e., saída definitiva)
dsort2app = {}   # internal_id -> {'my_id': int, 'last_box': tuple}
next_my_id = 1

# --- AUXILIARES ---
def compute_iou(box1, box2):
    x1,y1,w1,h1 = box1
    x2,y2,w2,h2 = box2
    xa = max(x1,x2)
    ya = max(y1,y2)
    xb = min(x1+w1, x2+w2)
    yb = min(y1+h1, y2+h2)
    iw = max(0, xb-xa)
    ih = max(0, yb-ya)
    inter = iw * ih
    union = w1*h1 + w2*h2 - inter
    return inter/union if union>0 else 0.0

# associação de detecção YOLO ao track do Deep SORT
def associate_detection_with_track(track_box, detections, allowed_class=None):
    tx = (track_box[0] + track_box[2]) / 2
    ty = (track_box[1] + track_box[3]) / 2
    best, bd = None, float('inf')
    for det in detections:
        if allowed_class and det['class'] != allowed_class:
            continue
        x,y,w,h = det['box']
        cx,cy = x + w/2, y + h/2
        d = ((tx-cx)**2 + (ty-cy)**2)**0.5
        if d < bd:
            bd, best = d, det
    return best

# detecta mudança significativa de estado
def state_changed(prev_state, curr_state, iou_thresh=0.96, pixel_tol=20):
    prev_prat, prev_box = prev_state
    curr_prat, curr_box = curr_state
    if prev_prat != curr_prat:
        return True
    iou = compute_iou(prev_box, curr_box)
    if iou >= iou_thresh:
        return False
    diffs = [abs(a-b) for a,b in zip(prev_box, curr_box)]
    return not all(d<=pixel_tol for d in diffs)

# atribuição de prateleira com histerese
def determinar_prateleira(center, rois, anterior=None, tol=40):
    x,y = center
    if anterior:
        for r in rois:
            if f"Prateleira {r['id']}" == anterior:
                if r['x1']-tol<=x<=r['x2']+tol and r['y1']-tol<=y<=r['y2']+tol:
                    return anterior
                break
    for r in rois:
        if r['x1']<=x<=r['x2'] and r['y1']<=y<=r['y2']:
            return f"Prateleira {r['id']}"
    return "Fora da prateleira"

# fluxo principal
def main():
    global next_my_id
    criar_tabela()
    rois = carregar_rois("data/annotations/rois_live.json")
    if not rois:
        print("Calibre as prateleiras primeiro.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Falha ao abrir webcam.")
        return

    last_time = time.time()
    estado = {}    # my_id -> (prateleira, box)
    classe = {}    # my_id -> classe
    ultima = {}    # my_id -> (prateleira, box)
    missing = {}   # my_id -> ciclos sem detecção
    prev_draw = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        now = time.time()

        if now - last_time >= detection_interval:
            pre = preprocess_for_shelf_detection(frame)
            detect_shelf_lines(pre)
            objs = [o for o in detect_objects(frame) if o['class'] in allowed_classes]

            dets = [([x,y,x+w,y+h], o['confidence'])
                    for o in objs for x,y,w,h in [o['box']]]
            tracks = tracker.update_tracks(dets, frame=frame)

            current_mids = set()
            curr_draw = []

            # processa cada track ativo
            for t in tracks:
                if not t.is_confirmed():
                    continue
                iid = t.track_id
                box_int = tuple(map(int, t.to_ltrb()))

                # mapeia internal_id para meu my_id
                if iid not in dsort2app:
                    dsort2app[iid] = {'my_id': next_my_id, 'last_box': box_int}
                    next_my_id += 1
                mid = dsort2app[iid]['my_id']
                dsort2app[iid]['last_box'] = box_int

                current_mids.add(mid)
                missing[mid] = 0

                det = associate_detection_with_track(box_int, objs, classe.get(mid))
                if not det:
                    continue
                x,y,w,h = det['box']
                cls = det['class']

                if mid not in classe:
                    classe[mid] = cls
                elif classe[mid] != cls:
                    # força saída da classe anterior e apaga estado
                    prat_old,_ = estado.get(mid, ("Desconhecida",()))
                    inserir_evento(mid, classe[mid], prat_old, "saída")
                    estado.pop(mid, None)
                    classe.pop(mid, None)
                    ultima.pop(mid, None)
                    missing.pop(mid, None)
                    continue

                adj = [x,y,w,h]
                center = (x + w/2, y + h/2)
                prat_prev = estado.get(mid, (None,))[0]
                prat_cur = determinar_prateleira(center, rois, prat_prev)

                new_state = (prat_cur, tuple(adj))
                old_state = estado.get(mid)

                if not old_state:
                    # entrada
                    if prat_cur != "Fora da prateleira":
                        inserir_evento(mid, cls, prat_cur, "entrada")
                    else:
                        inserir_evento(mid, cls, "Fora da prateleira", "não identificado")
                    inserir_deteccao(cls, mid, adj, True, None)
                    estado[mid] = new_state
                    ultima[mid] = new_state
                else:
                    if state_changed(old_state, new_state):
                        if old_state[0] != prat_cur:
                            if old_state[0] != "Fora da prateleira":
                                inserir_evento(mid, cls, old_state[0], "saída")
                            if prat_cur != "Fora da prateleira":
                                inserir_evento(mid, cls, prat_cur, "entrada")
                        if old_state[1] != tuple(adj):
                            inserir_deteccao(cls, mid, adj, True, None)
                        estado[mid] = new_state
                        ultima[mid] = new_state

                curr_draw.append((adj, cls, mid, prat_cur))

            last_time = now

            # dispara saída por ausência e limpa mapping de my_id
            for mid in list(estado):
                if mid not in current_mids:
                    missing[mid] = missing.get(mid, 0) + 1
                    if missing[mid] >= MISSING_THRESHOLD:
                        prat_old,_ = estado.pop(mid)
                        inserir_evento(mid, classe.pop(mid, "unknown"), prat_old, "saída")
                        ultima.pop(mid, None)
                        missing.pop(mid, None)
                        # limpa qualquer internal_id mapeado para este mid
                        for iid,info in list(dsort2app.items()):
                            if info['my_id'] == mid:
                                dsort2app.pop(iid, None)

            prev_draw = curr_draw

        # desenha os retângulos persistentes
        for b,cls,mid,prat in prev_draw:
            x,y,w,h = b
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

        # desenha ROIs
        for r in rois:
            cv2.rectangle(frame, (r['x1'],r['y1']), (r['x2'],r['y2']), (255,255,0), 2)
            cv2.putText(frame, f"Prateleira {r['id']}", (r['x1'],r['y1']-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 2)

        cv2.imshow("Deteccao e Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
