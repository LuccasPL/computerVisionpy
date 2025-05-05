# src/db.py
import mysql.connector
from mysql.connector import Error
import json

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '78517231Le!',
    'database': 'deteccoes_db'
}

def criar_conexao():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
    return None

def criar_tabela():
    conn = criar_conexao()
    if not conn:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    # Cria tabela Detecoes (sem extra_features)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Detecoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        objeto VARCHAR(255),
        track_id INT,
        x INT, y INT, w INT, h INT,
        alinhado BOOLEAN,
        line_y FLOAT
    );
    """)
    conn.commit()

    # Verifica se a coluna extra_features já existe
    cursor.execute("""
        SELECT COUNT(*) 
          FROM information_schema.columns
         WHERE table_schema = %s
           AND table_name = 'Detecoes'
           AND column_name = 'extra_features';
    """, (DB_CONFIG['database'],))
    count = cursor.fetchone()[0]
    if count == 0:
        try:
            cursor.execute("ALTER TABLE Detecoes ADD COLUMN extra_features JSON;")
            conn.commit()
            print("Coluna 'extra_features' adicionada com sucesso.")
        except Error as e:
            print(f"Erro ao adicionar coluna extra_features: {e}")

    cursor.close()
    conn.close()

def inserir_deteccao(objeto, track_id, box, alinhado, line_y, extra_features=None):
    x, y, w, h = box
    conn = criar_conexao()
    if not conn:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    insert = """
    INSERT INTO Detecoes
      (objeto, track_id, x, y, w, h, alinhado, line_y, extra_features)
    VALUES
      (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    data = (
        objeto, track_id, x, y, w, h,
        alinhado, line_y if line_y is not None else 0,
        json.dumps(extra_features) if extra_features is not None else None
    )
    try:
        cursor.execute(insert, data)
        conn.commit()
    except Error as e:
        print(f"Erro ao inserir detecção: {e}")
    finally:
        cursor.close()
        conn.close()

def inserir_evento(track_id, objeto, prateleira, evento):
    conn = criar_conexao()
    if not conn:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    insert = """
      INSERT INTO Eventos (track_id, objeto, prateleira, evento)
      VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(insert, (track_id, objeto, prateleira, evento))
        conn.commit()
    except Error as e:
        print(f"Erro ao inserir evento: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    criar_tabela()
