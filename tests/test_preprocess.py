# tests/test_preprocess.py

import unittest
import os
from src import preprocess

class TestPreprocess(unittest.TestCase):
    def test_preprocess_image(self):
        input_path = "data/test_raw/img_000.jpg"
        output_path = "data/test_processed/img_000_processed.jpg"
        os.makedirs("data/test_raw/", exist_ok=True)
        os.makedirs("data/test_processed/", exist_ok=True)
        # Crie uma imagem de teste (exemplo: uma imagem preta)
        import numpy as np
        import cv2
        dummy_image = (np.zeros((480, 640, 3)) + 255).astype("uint8")
        cv2.imwrite(input_path, dummy_image)
        preprocess.preprocess_image(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))

if __name__ == "__main__":
    unittest.main()
