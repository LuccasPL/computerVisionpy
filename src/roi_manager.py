import json, os

def carregar_prateleiras(caminho="data/annotations/rois_prateleiras.json"):
    """
    Carrega ROIs de prateleiras do JSON.
    Cada item deve ter: id, x1, y1, x2, y2
    """
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        rois = json.load(f)
    # garante que cada ROI tenha um id
    for idx, r in enumerate(rois, start=1):
        r.setdefault("id", idx)
    return rois

def carregar_posicoes(caminho="data/annotations/rois_posicoes.json"):
    """
    Carrega ROIs de posições do JSON.
    Cada item deve ter: shelf_id, pos_id, x1, y1, x2, y2
    """
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        pos = json.load(f)
    # garante pos_id e shelf_id válidos
    for p in pos:
        if "shelf_id" not in p or "pos_id" not in p:
            raise ValueError("Cada posição precisa de shelf_id e pos_id no JSON.")
    return pos

def verificar_prateleira(point, prateleiras):
    """
    Retorna (True, roi) se point estiver dentro de alguma prateleira.
    """
    x,y = point
    for r in prateleiras:
        if r["x1"] <= x <= r["x2"] and r["y1"] <= y <= r["y2"]:
            return True, r
    return False, None

def verificar_posicao(point, posicoes):
    """
    Retorna (True, roi) se point estiver dentro de alguma posição, else (False, None).
    """
    x,y = point
    for p in posicoes:
        if p["x1"] <= x <= p["x2"] and p["y1"] <= y <= p["y2"]:
            return True, p
    return False, None
