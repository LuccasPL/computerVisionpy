from flask import Flask, render_template, request
import mysql.connector
from mysql.connector import Error
import csv
from flask import Response

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',       
    'user': 'root',      
    'password': '78517231Le!',    
    'database': 'deteccoes_db'  
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print("Erro ao conectar ao MySQL:", e)
        return None

@app.route("/", methods=["GET"])
def index():
    # Recupera os parâmetros de filtro da URL (se existirem)
    data_inicial = request.args.get("data_inicial")
    data_final = request.args.get("data_final")
    prateleira_filtro = request.args.get("prateleira")
    
    conn = get_connection()
    if conn is None:
        return "Erro na conexão com o banco de dados."
    
    cursor = conn.cursor(dictionary=True)
    
    # Consulta 1: Total de entradas por prateleira, com filtro opcional
    query1 = "SELECT prateleira, COUNT(*) AS total_entradas FROM Eventos WHERE evento = 'entrada'"
    params = []
    if prateleira_filtro:
        query1 += " AND prateleira = %s"
        params.append(prateleira_filtro)
    query1 += " GROUP BY prateleira;"
    cursor.execute(query1, params)
    entradas_por_prateleira = cursor.fetchall()
    
    # Consulta 2: Eventos por data, com filtro de datas se fornecido
    query2 = "SELECT DATE(timestamp) AS data, COUNT(*) AS total_eventos FROM Eventos WHERE 1=1"
    params = []
    if data_inicial:
        query2 += " AND timestamp >= %s"
        params.append(data_inicial)
    if data_final:
        query2 += " AND timestamp <= %s"
        params.append(data_final)
    query2 += " GROUP BY DATE(timestamp) ORDER BY data;"
    cursor.execute(query2, params)
    eventos_por_data = cursor.fetchall()

    # Consulta 3: Os 10 eventos mais recentes (podemos deixar sem filtro ou aplicar os filtros também)
    query3 = "SELECT track_id, objeto, prateleira, evento, timestamp FROM Eventos"
    filters = []
    params = []
    if data_inicial:
        filters.append("timestamp >= %s")
        params.append(data_inicial)
    if data_final:
        filters.append("timestamp <= %s")
        params.append(data_final)
    if prateleira_filtro:
        filters.append("prateleira = %s")
        params.append(prateleira_filtro)
    if filters:
        query3 += " WHERE " + " AND ".join(filters)
    query3 += " ORDER BY timestamp DESC LIMIT 10;"
    cursor.execute(query3, params)
    eventos_recentes = cursor.fetchall()
    
    # Consulta 4: Total de eventos para resumo (com filtro se desejado)
    query4 = "SELECT COUNT(*) AS total_eventos FROM Eventos WHERE 1=1"
    params = []
    if data_inicial:
        query4 += " AND timestamp >= %s"
        params.append(data_inicial)
    if data_final:
        query4 += " AND timestamp <= %s"
        params.append(data_final)
    cursor.execute(query4, params)
    total_eventos = cursor.fetchone()["total_eventos"]

    cursor.close()
    conn.close()
    
    return render_template("dashboard.html",
                           entradas=entradas_por_prateleira,
                           eventos=eventos_por_data,
                           recentes=eventos_recentes,
                           total_eventos=total_eventos,
                           data_inicial=data_inicial or "",
                           data_final=data_final or "",
                           prateleira_filtro=prateleira_filtro or "")

@app.route("/export")
def export_csv():
    # Recupera os parâmetros de filtro da query string
    data_inicial = request.args.get("data_inicial")
    data_final = request.args.get("data_final")
    prateleira_filtro = request.args.get("prateleira")
    
    conn = get_connection()
    if conn is None:
        return "Erro na conexão com o banco de dados."
    
    cursor = conn.cursor(dictionary=True)
    
    # Consulta para exportar os eventos filtrados
    query = "SELECT * FROM Eventos WHERE 1=1"
    params = []
    if data_inicial:
        query += " AND timestamp >= %s"
        params.append(data_inicial)
    if data_final:
        query += " AND timestamp <= %s"
        params.append(data_final)
    if prateleira_filtro:
        query += " AND prateleira = %s"
        params.append(prateleira_filtro)
    query += " ORDER BY timestamp DESC;"
    cursor.execute(query, params)
    eventos = cursor.fetchall()
    cursor.close()
    conn.close()
    
    def generate():
        data = []
        header = eventos[0].keys() if eventos else []
        data.append(",".join(header) + "\n")
        for row in eventos:
            data.append(",".join(str(row[col]) for col in header) + "\n")
        return "".join(data)
    
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=eventos.csv"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
