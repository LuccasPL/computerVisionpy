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

def inserir_deteccao(objeto, box, alinhado, line_y):
    """Insere uma detecção no banco de dados."""
    x, y, w, h = box
    conn = criar_conexao()
    if conn is None:
        print("Erro: conexão não estabelecida!")
        return
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO Detecoes (objeto, x, y, w, h, alinhado, line_y)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    data = (objeto, x, y, w, h, alinhado, line_y if line_y is not None else 0)
    try:
        cursor.execute(insert_query, data)
        conn.commit()
        print(f"Detecção inserida: {objeto} em ({x}, {y}, {w}, {h}) | Alinhado: {alinhado}")
    except Error as e:
        print(f"Erro ao inserir a detecção: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    criar_tabela()
    # Teste de inserção
    inserir_deteccao("caixa", [100, 150, 50, 60], True, 200)
