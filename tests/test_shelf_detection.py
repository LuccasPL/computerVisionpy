# tests/test_shelf_detection.py

import unittest
import cv2
import numpy as np
from src.shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned

class TestShelfDetection(unittest.TestCase):

    def setUp(self):
        # Cria uma imagem dummy (branca) para teste
        self.dummy_image = np.ones((416, 416, 3), dtype="uint8") * 255
        # Desenha uma linha horizontal simulando uma prateleira
        cv2.line(self.dummy_image, (50, 200), (366, 200), (0, 0, 0), 2)

    def test_preprocess(self):
        processed = preprocess_for_shelf_detection(self.dummy_image)
        self.assertEqual(processed.shape, (416, 416))

    def test_detect_lines(self):
        processed = preprocess_for_shelf_detection(self.dummy_image)
        lines = detect_shelf_lines(processed, canny_threshold1=50, canny_threshold2=150, hough_threshold=100)
        self.assertTrue(len(lines) > 0, "Deve detectar pelo menos uma linha.")

    def test_alignment(self):
        # Suponha que um objeto esteja com a caixa [x, y, w, h]
        object_box = [100, 180, 50, 40]  # Centro em y ~ 200
        processed = preprocess_for_shelf_detection(self.dummy_image)
        lines = detect_shelf_lines(processed, canny_threshold1=50, canny_threshold2=150, hough_threshold=100)
        aligned, line_y = is_aligned(object_box, lines, tolerance=20)
        self.assertTrue(aligned, "O objeto deve estar alinhado com a prateleira.")

if __name__ == '__main__':
    unittest.main()
