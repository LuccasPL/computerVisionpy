import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines
from roi_manager import carregar_rois
from db import criar_tabela, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# --- CONFIGURAÇÕES ---
allowed_classes    = ["sports ball", "tennis racket"]
tracker            = DeepSort(max_age=2, n_init=3, nn_budget=100, override_track_class=None, embedder="mobilenet")
detection_interval = 5.0      # segundos entre detecções
MISSING_THRESHOLD  = 2        # ciclos sem detecção para saída

# Mapeamento interno → nosso ID persistente
dsort2app = {}
next_my_id = 1

# Estados e ocupação de prateleiras
estado          = {}  # mid -> última bbox
classe          = {}  # mid -> classe fixa
ultima_ins      = {}  # mid -> timestamp da última inserção
missing         = {}  # mid -> contagem de frames ausentes
shelf_occupancy = {}  # "Prateleira N" -> mid atualmente dentro

def compute_iou(a, b):
    xA = max(a[0], b[0]); yA = max(a[1], b[1])
    xB = min(a[0]+a[2], b[0]+b[2]); yB = min(a[1]+a[3], b[1]+b[3])
    interW = max(0, xB-xA); interH = max(0, yB-yA)
    inter  = interW*interH
    union  = a[2]*a[3] + b[2]*b[3] - inter
    return inter/union if union>0 else 0

def state_changed(old_box, new_box, iou_thresh=0.96):
    return compute_iou(old_box, new_box) < iou_thresh

def determinar_prateleira(center, rois):
    x,y = center
    for r in rois:
        if r['x1'] <= x <= r['x2'] and r['y1'] <= y <= r['y2']:
            return f"Prateleira {r['id']}"
    return "Fora da prateleira"

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
    prev_draw = []  # <-- inicializado antes do loop

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        if now - last_time >= detection_interval:
            # 1) detecta objetos e tracks
            pre = preprocess_for_shelf_detection(frame)
            _   = detect_shelf_lines(pre)
            objs = [o for o in detect_objects(frame) if o['class'] in allowed_classes]
            dets = [([x,y,x+w,y+h], o['confidence']) for o in objs for x,y,w,h in [o['box']]]
            tracks = tracker.update_tracks(dets, frame=frame)

            current_mids = set()
            curr_draw    = []

            # 2) processa cada track confirmado
            for t in tracks:
                if not t.is_confirmed():
                    continue
                iid = t.track_id
                x1,y1,x2,y2 = map(int, t.to_ltrb())
                w, h = x2-x1, y2-y1

                # atribui nosso ID
                if iid not in dsort2app:
                    dsort2app[iid] = next_my_id
                    next_my_id += 1
                mid = dsort2app[iid]
                current_mids.add(mid)
                missing[mid] = 0

                # associa detecção YOLO mais próxima
                best = None; bd = float('inf')
                tx,ty = (x1+x2)/2, (y1+y2)/2
                for o in objs:
                    bx,by,bw,bh = o['box']
                    cx,cy = bx + bw/2, by + bh/2
                    d = np.hypot(tx-cx, ty-cy)
                    if d < bd:
                        bd,best = d,o
                if best is None:
                    continue

                cls = best['class']
                bx,by,bw,bh = best['box']

                # fixa classe
                if mid not in classe:
                    classe[mid] = cls
                elif classe[mid] != cls:
                    continue  # ignora troca de classe inesperada

                # determina prateleira
                center = (bx + bw/2, by + bh/2)
                prat = determinar_prateleira(center, rois)

                # registro de ENTRADA (só se prateleira estiver livre)
                if mid not in estado and prat != "Fora da prateleira":
                    if prat not in shelf_occupancy:
                        inserir_evento(mid, cls, prat, "entrada")
                        shelf_occupancy[prat] = mid

                # atualiza estado
                old_box = estado.get(mid)
                new_box = (bx,by,bw,bh)
                if old_box is None or state_changed(old_box, new_box):
                    estado[mid] = new_box
                    ultima_ins[mid] = now

                curr_draw.append((bx,by,bw,bh,cls,mid,prat))

            last_time = now

            # 3) dispara saída por ausência
            for mid in list(estado):
                if mid not in current_mids:
                    missing[mid] = missing.get(mid,0) + 1
                    if missing[mid] >= MISSING_THRESHOLD:
                        # encontra e libera prateleira
                        prat = next((p for p,m in shelf_occupancy.items() if m==mid), None)
                        if prat:
                            inserir_evento(mid, classe.get(mid,"unknown"), prat, "saída")
                            shelf_occupancy.pop(prat, None)
                        # limpa estados
                        estado.pop(mid, None)
                        classe.pop(mid, None)
                        ultima_ins.pop(mid, None)
                        missing.pop(mid, None)

            prev_draw = curr_draw

        # 4) desenha as caixas persistentes
        for bx,by,bw,bh,cls,mid,prat in prev_draw:
            cv2.rectangle(frame, (int(bx),int(by)), (int(bx+bw),int(by+bh)), (0,255,0), 2)
            cv2.putText(frame, f"{cls} (ID {mid})",
                        (int(bx), int(by)-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        # 5) desenha ROIs
        for r in rois:
            cv2.rectangle(frame,
                          (r['x1'],r['y1']),
                          (r['x2'],r['y2']),
                          (255,255,0), 2)
            cv2.putText(frame,
                        f"Prateleira {r['id']}",
                        (r['x1'], r['y1']-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)

        cv2.imshow("Detecção e Eventos", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
