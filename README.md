# Sistema de Controlo de Armazém Inteligente

Este projeto implementa um sistema inteligente para controlo de armazém utilizando webcam e algoritmos de detecção de objetos.

## Estrutura do Projeto

- **data/**: Dados brutos, processados e anotações.
- **models/**: Arquivos do modelo (YOLO, etc.).
- **src/**: Código fonte do sistema.
  - `capture.py`: Captura de imagens da webcam.
  - `preprocess.py`: Pré-processamento de imagens.
  - `train.py`: (Opcional) Treinamento do modelo.
  - `detection.py`: Inferência com o modelo.
  - `api.py`: API para detecção.
  - `dashboard.py`: Dashboard de monitoramento.
  - `utils.py`: Funções utilitárias.
- **tests/**: Testes unitários.
- **docs/**: Documentação do projeto.

## Instalação

1. Clone o repositório.
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
