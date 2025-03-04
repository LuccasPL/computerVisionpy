# tests/test_capture.py

import unittest
import os
from src import capture

class TestCapture(unittest.TestCase):
    def test_capture_images(self):
        output_dir = "data/test_raw/"
        # Remove o diretório se existir, para um teste limpo
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
        # Captura 5 imagens para teste
        capture.capture_images(output_dir=output_dir, num_images=5)
        # Verifica se 5 imagens foram salvas
        files = os.listdir(output_dir)
        self.assertEqual(len(files), 5)

if __name__ == "__main__":
    unittest.main()
