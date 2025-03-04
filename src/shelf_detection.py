# src/shelf_detection.py

import cv2
import numpy as np

def preprocess_for_shelf_detection(frame):
    """
    Converte a imagem para escala de cinza e aplica desfoque para reduzir o ruído.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return blurred

def detect_shelf_lines(preprocessed_img, canny_threshold1=50, canny_threshold2=150, hough_threshold=200):
    """
    Detecta linhas na imagem pré-processada usando Canny e a transformada de Hough.
    Retorna uma lista de tuplas (rho, theta) representando as linhas.
    """
    edges = cv2.Canny(preprocessed_img, canny_threshold1, canny_threshold2)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, hough_threshold)
    shelf_lines = []
    if lines is not None:
        for line in lines:
            rho, theta = line[0]
            # Seleciona linhas aproximadamente horizontais (theta próximo de 0 ou pi)
            if theta < np.pi / 4 or theta > 3 * np.pi / 4:
                shelf_lines.append((rho, theta))
    return shelf_lines

def get_line_y_coordinate(rho, theta, x):
    """
    Converte a equação da linha (rho, theta) para obter a coordenada y para um valor x.
    A equação: x*cos(theta) + y*sin(theta) = rho  =>  y = (rho - x*cos(theta)) / sin(theta)
    """
    return (rho - x * np.cos(theta)) / np.sin(theta)

def is_aligned(object_box, shelf_lines, tolerance=20):
    """
    Verifica se o objeto (bounding box) está alinhado com alguma das linhas (prateleiras).
    Retorna um tupla (True/False, y_line) onde y_line é a posição da prateleira detectada.
    """
    x, y, w, h = object_box
    center_y = y + h // 2
    for rho, theta in shelf_lines:
        y_line = get_line_y_coordinate(rho, theta, x + w // 2)
        if abs(center_y - y_line) < tolerance:
            return True, y_line
    return False, None
