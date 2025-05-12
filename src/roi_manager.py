import json
import os

def carregar_prateleiras(caminho="data/annotations/rois_prateleiras.json"):
    """
    Carrega as ROIs de prateleiras.
    """
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r") as f:
        return json.load(f)

def carregar_posicoes(caminho="data/annotations/rois_posicoes.json"):
    """
    Carrega as ROIs de posições dentro das prateleiras.
    """
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r") as f:
        return json.load(f)

def verificar_prateleira(point, prateleiras):
    """
    Dado um ponto (x,y), retorna (True, prateleira_dict) se dentro de alguma prateleira.
    """
    x,y = point
    for pr in prateleiras:
        if pr["x1"] <= x <= pr["x2"] and pr["y1"] <= y <= pr["y2"]:
            return True, pr
    return False, None

def verificar_posicao(point, posicoes):
    """
    Dado um ponto (x,y), retorna (True, posicao_dict) se dentro de alguma posição.
    """
    x,y = point
    for pos in posicoes:
        if pos["x1"] <= x <= pos["x2"] and pos["y1"] <= y <= pos["y2"]:
            return True, pos
    return False, None
