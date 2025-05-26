import mysql.connector
from mysql.connector import Error

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
    except Error:
        return None

def criar_tabelas():
    conn = criar_conexao()
    if not conn: 
        print("Falha conexão DB.")
        return
    cur = conn.cursor()
    # Detecções
    cur.execute("""
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
    # Eventos agora com coluna posicao
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Eventos (
      id INT AUTO_INCREMENT PRIMARY KEY,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      track_id INT,
      objeto VARCHAR(255),
      prateleira VARCHAR(100),
      posicao VARCHAR(100),
      evento VARCHAR(50)
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

def inserir_deteccao(objeto, track_id, box, alinhado, line_y):
    x,y,w,h = box
    conn = criar_conexao()
    if not conn: return
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO Detecoes (objeto, track_id, x, y, w, h, alinhado, line_y)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (objeto, track_id, x, y, w, h, alinhado, line_y or 0))
    conn.commit()
    cur.close()
    conn.close()

def inserir_evento(track_id, objeto, prateleira, posicao, evento):
    conn = criar_conexao()
    if not conn: return
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO Eventos (track_id, objeto, prateleira, posicao, evento)
      VALUES (%s,%s,%s,%s,%s)
    """, (track_id, objeto, prateleira, posicao, evento))
    conn.commit()
    cur.close()
    conn.close()
