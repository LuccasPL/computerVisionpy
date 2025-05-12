# src/capture.py
import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines
from roi_manager import carregar_prateleiras, carregar_posicoes, verificar_prateleira, verificar_posicao
from db import criar_tabela, inserir_deteccao, inserir_evento
from deep_sort_realtime.deepsort_tracker import DeepSort

# --- CONFIGURAÇÕES ---
allowed_classes = ["sports ball", "tennis racket"]
tracker = DeepSort(max_age=2, n_init=3, nn_budget=100, override_track_class=None, embedder="mobilenet")
detection_interval = 5.0  # segundos entre detecções
MISSING_THRESHOLD = 2      # ciclos sem detecção para saída

# Mapeamento interno do DeepSORT → nosso my_id único
dsort2app = {}   # internal_id -> my_id
next_my_id = 1

# Estados persistentes
# estado: my_id -> { 'pos_id': int, 'shelf': str, 'cls': str }
estado = {}
# pos_occupied: pos_id -> my_id
pos_occupied = {}
missing = {}      # my_id -> ciclos sem detecção
prev_draw = []    # caixas a desenhar

# Auxiliar: associa detecção YOLO ao track com base em centro
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

# Fluxo principal
def main():
    global next_my_id, estado, pos_occupied, missing, prev_draw

    criar_tabela()
    prateleiras = carregar_prateleiras()
    posicoes = carregar_posicoes()
    if not prateleiras or not posicoes:
        print("Calibre prateleiras e posicoes primeiro (execute calibracao_grid.py).")
        return

    cap = cv2.VideoCapture(0)
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

        # Etapa de detecção periódica
        if now - last_time >= detection_interval:
            last_time = now
            # Pré-processamento (opcional)
            pre = preprocess_for_shelf_detection(frame)
            _ = detect_shelf_lines(pre)

            # Detecta objetos com YOLO
            dets_yolo = detect_objects(frame)
            objs = [o for o in dets_yolo if o['class'] in allowed_classes]

            # Prepara entradas para DeepSORT
            ds_inputs = [([x,y,x+w,y+h], o['confidence'])
                         for o in objs for x,y,w,h in [o['box']]]
            tracks = tracker.update_tracks(ds_inputs, frame=frame)

            current_mids = set()

            for tr in tracks:
                if not tr.is_confirmed():
                    continue
                iid = tr.track_id
                # Mapeia internal_id → my_id
                if iid not in dsort2app:
                    dsort2app[iid] = next_my_id
                    next_my_id += 1
                mid = dsort2app[iid]
                current_mids.add(mid)
                missing[mid] = 0

                # Associação YOLO → track para obter classe e bbox
                bbox4 = tr.to_ltrb()  # [x1,y1,x2,y2]
                det = associate_detection_with_track(bbox4, objs, estado.get(mid, {}).get('cls'))
                if not det:
                    continue
                x,y,w,h = det['box']
                cls = det['class']

                # Garante classe fixa por track
                if mid not in estado:
                    estado[mid] = {}
                if 'cls' not in estado[mid]:
                    estado[mid]['cls'] = cls

                # Determina shelf e posicao
                cx, cy = x + w/2, y + h/2
                ok_shelf, pr = verificar_prateleira((cx,cy), prateleiras)
                shelf_name = f"Prateleira {pr['id']}" if ok_shelf else "Fora da prateleira"
                ok_pos, pos = verificar_posicao((cx,cy), posicoes)
                pos_id = pos['id'] if ok_pos else None

                # Se primeira vez ou mid não estava em estado
                if 'pos_id' not in estado[mid]:
                    # Só registra entrada se posicao válida e livre
                    if pos_id and pos_id not in pos_occupied:
                        inserir_evento(mid, cls, shelf_name, "entrada")
                        inserir_deteccao(cls, mid, (x,y,w,h), True, None)
                        estado[mid]['pos_id'] = pos_id
                        estado[mid]['shelf'] = shelf_name
                        pos_occupied[pos_id] = mid
                    else:
                        # posição ocupada ou inválida → ignora
                        continue
                # Atualiza desenho
                curr_draw.append(((x,y,w,h), cls, mid, shelf_name))

            # Registra saída por ausência
            for mid in list(estado.keys()):
                if mid not in current_mids:
                    missing[mid] += 1
                    if missing[mid] >= MISSING_THRESHOLD:
                        pos_id_old = estado[mid].get('pos_id')
                        shelf_old = estado[mid].get('shelf')
                        cls_old = estado[mid].get('cls')
                        inserir_evento(mid, cls_old, shelf_old, "saída")
                        # libera posição
                        if pos_id_old in pos_occupied:
                            del pos_occupied[pos_id_old]
                        # limpa estado
                        del estado[mid]
                        del missing[mid]
                        # limpa mapping inverso
                        for k,v in list(dsort2app.items()):
                            if v == mid:
                                del dsort2app[k]

            prev_draw = curr_draw

        # Desenha resultados persistentes
        for (x,y,w,h), cls, mid, shelf_name in prev_draw:
            cv2.rectangle(frame, (int(x),int(y)), (int(x+w),int(y+h)), (0,255,0), 2)
            cv2.putText(frame, f"{cls} (ID {mid})", (int(x),int(y)-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        # Desenha ROIs de prateleiras e posicoes
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
