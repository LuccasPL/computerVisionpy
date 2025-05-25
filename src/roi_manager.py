import json, os

def carregar_prateleiras(caminho="data/annotations/rois_prateleiras.json"):
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r") as f:
        return json.load(f)

def carregar_posicoes(caminho="data/annotations/rois_posicoes.json"):
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r") as f:
        return json.load(f)

def verificar_prateleira(point, prateleiras):
    x, y = point
    for pr in prateleiras:
        if pr["x1"] <= x <= pr["x2"] and pr["y1"] <= y <= pr["y2"]:
            return True, pr
    return False, None

def verificar_posicao(point, posicoes):
    x, y = point
    for po in posicoes:
        if po["x1"] <= x <= po["x2"] and po["y1"] <= y <= po["y2"]:
            return True, po
    return False, None
