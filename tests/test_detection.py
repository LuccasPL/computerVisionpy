# tests/test_detection.py

import unittest
import cv2
from src import detection

class TestDetection(unittest.TestCase):
    def test_detect_objects(self):
        # Use uma imagem dummy com uma forma simples
        import numpy as np
        dummy_image = np.ones((416, 416, 3), dtype="uint8") * 255
        results = detection.detect_objects(dummy_image)
        # Como a imagem é branca, provavelmente não haverá detecções
        self.assertIsInstance(results, list)

if __name__ == "__main__":
    unittest.main()
