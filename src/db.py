import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': '78517231Le!',
    'database': 'deteccoes_db'
}

def criar_conexao():
    try:
        c = mysql.connector.connect(**DB_CONFIG)
        if c.is_connected():
            return c
    except Error as e:
        print(f"Erro ao conectar: {e}")
    return None

def criar_tabelas():
    conn = criar_conexao()
    if not conn:
        print("Não conectou ao MySQL!")
        return
    cur = conn.cursor()
    # Detecoes
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
    # Eventos agora com posicao
    cur.execute("""
      CREATE TABLE IF NOT EXISTS Eventos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        track_id INT,
        objeto VARCHAR(255),
        prateleira VARCHAR(50),
        posicao   VARCHAR(50),
        evento    VARCHAR(20)
      );
    """)
    # adiciona coluna posicao se faltar
    cur.execute("""
      SELECT COUNT(*) 
        FROM information_schema.columns
       WHERE table_schema=%s
         AND table_name='Eventos'
         AND column_name='posicao';
    """, (DB_CONFIG['database'],))
    if cur.fetchone()[0] == 0:
        try:
            cur.execute("ALTER TABLE Eventos ADD COLUMN posicao VARCHAR(50) AFTER prateleira;")
        except Error as e:
            print(f"Erro ao adicionar posicao: {e}")
    conn.commit()
    cur.close()
    conn.close()

def inserir_deteccao(objeto, track_id, box, alinhado, line_y):
    x,y,w,h = box
    conn = criar_conexao()
    if not conn:
        print("Erro conexão.")
        return
    cur = conn.cursor()
    try:
        cur.execute("""
          INSERT INTO Detecoes(objeto,track_id,x,y,w,h,alinhado,line_y)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s);
        """, (objeto,track_id,x,y,w,h,alinhado,line_y or 0))
        conn.commit()
    except Error as e:
        print(f"Erro ao inserir detecção: {e}")
    finally:
        cur.close()
        conn.close()

def inserir_evento(track_id, objeto, prateleira, posicao, evento):
    conn = criar_conexao()
    if not conn:
        print("Erro conexão.")
        return
    cur = conn.cursor()
    try:
        cur.execute("""
          INSERT INTO Eventos(track_id,objeto,prateleira,posicao,evento)
          VALUES(%s,%s,%s,%s,%s);
        """, (track_id,objeto,prateleira,posicao,evento))
        conn.commit()
    except Error as e:
        print(f"Erro ao inserir evento: {e}")
    finally:
        cur.close()
        conn.close()
