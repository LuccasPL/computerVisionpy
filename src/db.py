import mysql.connector
from mysql.connector import Error

# Configurações para conectar ao MySQL
DB_CONFIG = {
    'host': 'localhost',       
    'user': 'root',      
    'password': '78517231Le!',    
    'database': 'deteccoes_db'  
}

def criar_conexao():
    """Cria e retorna uma conexão com o banco de dados MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
    return None

def criar_tabela():
    """Cria a tabela de detecções se ela não existir."""
    conn = criar_conexao()
    if conn is None:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS Detecoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        objeto VARCHAR(255),
        x INT,
        y INT,
        w INT,
        h INT,
        alinhado BOOLEAN,
        line_y FLOAT
    );
    """
    try:
        cursor.execute(create_table_query)
        conn.commit()
        print("Tabela 'Detecoes' criada com sucesso (ou já existe).")
    except Error as e:
        print(f"Erro ao criar a tabela: {e}")
    finally:
        cursor.close()
        conn.close()

def inserir_deteccao(objeto, track_id, box, alinhado, line_y):
    x, y, w, h = box
    conn = criar_conexao()
    if conn is None:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO Detecoes (objeto, track_id, x, y, w, h, alinhado, line_y)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    data = (objeto, track_id, x, y, w, h, alinhado, line_y if line_y is not None else 0)
    try:
        cursor.execute(insert_query, data)
        conn.commit()
        print(f"Detecção inserida: {objeto} (ID {track_id}) em ({x}, {y}, {w}, {h}) | Alinhado: {alinhado}")
    except Error as e:
        print(f"Erro ao inserir a detecção: {e}")
    finally:
        cursor.close()
        conn.close()

def inserir_evento(track_id, objeto, prateleira, evento):
    """Insere um evento (entrada, saída, troca) no banco de dados."""
    conn = criar_conexao()
    if conn is None:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO Eventos (track_id, objeto, prateleira, evento)
        VALUES (%s, %s, %s, %s)
    """
    data = (track_id, objeto, prateleira, evento)
    try:
        cursor.execute(insert_query, data)
        conn.commit()
        print(f"Evento inserido: Objeto '{objeto}' (ID {track_id}) - {evento} na prateleira {prateleira}")
    except Exception as e:
        print(f"Erro ao inserir o evento: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    criar_tabela()
    # Teste de inserção:
    inserir_deteccao("person", 1, [100, 150, 50, 60], True, 200)
