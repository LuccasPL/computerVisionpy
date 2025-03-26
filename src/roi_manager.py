import json

def carregar_rois(caminho="data\annotations\rois_live.json"):
    """
    Carrega as ROIs salvas em formato JSON.
    Cada ROI deve estar em um dicionário com as chaves:
    "x1", "y1", "x2", "y2".
    """
    try:
        with open(caminho, "r") as f:
            rois = json.load(f)
        return rois
    except Exception as e:
        print(f"Erro ao carregar as ROIs: {e}")
        return []

def verificar_roi(obj_center, rois):
    """
    Verifica se o ponto (obj_center) está dentro de alguma ROI.
    - obj_center: tupla (x, y)
    - rois: lista de dicionários com 'x1', 'y1', 'x2' e 'y2'
    
    Retorna uma tupla (True/False, roi) onde 'roi' é a ROI na qual o objeto foi encontrado.
    """
    for index, roi in enumerate(rois, start=1):
        if roi["x1"] <= obj_center[0] <= roi["x2"] and roi["y1"] <= obj_center[1] <= roi["y2"]:
            # Se desejar, pode incluir um identificador na ROI:
            roi["id"] = index
            return True, roi
    return False, None
