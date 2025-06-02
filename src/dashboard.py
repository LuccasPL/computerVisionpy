from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import csv
import io
import cv2  # para o feed da câmera

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
socketio = SocketIO(app, cors_allowed_origins='*')

# ----------------------------
# 1) CONFIGURAÇÃO DE LOGIN
# ----------------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id_, username, password_hash):
        self.id = id_
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, password_hash FROM Usuarios WHERE id=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return User(row['id'], row['username'], row['password_hash'])
    return None

def init_users_table():
    conn = get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(150) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        );
        """
    )
    conn.commit()
    cursor.close()
    conn.close()

# ----------------------------
# 2) CONFIGURAÇÃO DO BD MySQL
# ----------------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '78517231Le!',
    'database': 'deteccoes_db'
}

def get_connection():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print("Erro ao conectar ao MySQL:", e)
        return None

# ----------------------------
# 3) CONFIGURAÇÃO DO CAMERA STREAM
# ----------------------------
camera = cv2.VideoCapture(0)

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(
        gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# ----------------------------
# 4) ROTAS DE AUTENTICAÇÃO
# ----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('Preencha todos os campos.', 'warning')
            return render_template('register.html')
        hash_ = generate_password_hash(password)
        conn = get_connection()
        if not conn:
            flash('Erro na conexão com o BD.', 'danger')
            return render_template('register.html')
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Usuarios (username, password_hash) VALUES (%s, %s)",
                (username, hash_)
            )
            conn.commit()
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Error:
            flash('Username já existe.', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_connection()
        if not conn:
            flash('Erro na conexão com o BD.', 'danger')
            return render_template('login.html')
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, password_hash FROM Usuarios WHERE username=%s",
            (username,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['password_hash'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login inválido.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ----------------------------
# 5) API: HISTÓRICO DE EVENTOS POR PRATELEIRA
# ----------------------------
@app.route('/api/prateleira/<int:prat_id>/history')
@login_required
def shelf_history(prat_id):
    prat_str = f'Prateleira {prat_id}'
    conn = get_connection()
    if not conn:
        return jsonify(history=[])
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT track_id, objeto, posicao, evento, timestamp
        FROM Eventos
        WHERE prateleira = %s
        ORDER BY timestamp DESC
        """,
        (prat_str,)
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(history=history)

# ----------------------------
# 6) ROTA /limpar_pendentes (marca saída para itens “presos”)
# ----------------------------
@app.route('/limpar_pendentes', methods=['POST'])
@login_required
def clear_pending_entries():
    conn = get_connection()
    if not conn:
        flash('Erro ao tentar limpar pendentes.', 'danger')
        return redirect(url_for('dashboard'))

    cursor = conn.cursor(dictionary=True)
    # Seleciona todos cujo último evento foi 'entrada'
    cursor.execute(
        """
        SELECT e.track_id, e.objeto
        FROM Eventos e
        JOIN (
            SELECT track_id, MAX(timestamp) AS maxt
            FROM Eventos
            GROUP BY track_id
        ) m ON e.track_id = m.track_id AND e.timestamp = m.maxt
        WHERE e.evento = 'entrada';
        """
    )
    rows = cursor.fetchall()
    if not rows:
        cursor.close()
        conn.close()
        flash('Não há itens pendentes para limpar.', 'info')
        return redirect(url_for('dashboard'))

    # Insere evento de 'saída' para cada um
    for r in rows:
        cursor.execute(
            """
            INSERT INTO Eventos (track_id, objeto, prateleira, posicao, evento, timestamp)
            VALUES (%s, %s, %s, %s, %s, NOW());
            """,
            (r['track_id'], r['objeto'], 'Fora da prateleira', None, 'saída')
        )
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'{len(rows)} item(ns) marcados como saída.', 'success')
    return redirect(url_for('dashboard'))

# ----------------------------
# 7) ROTA PRINCIPAL: DASHBOARD
# ----------------------------
@app.route('/', methods=['GET'])
@login_required
def dashboard():
    # 7.1) Filtros
    data_inicial      = request.args.get('data_inicial')
    data_final        = request.args.get('data_final')
    prateleira_filtro = request.args.get('prateleira')
    classes_filtro    = request.args.getlist('classe')

    conn = get_connection()
    if not conn:
        return 'Erro na conexão com o banco de dados.'
    cursor = conn.cursor(dictionary=True)

    # 7.2) Todas as classes únicas
    cursor.execute("SELECT DISTINCT objeto FROM Eventos")
    all_classes = [r['objeto'] for r in cursor.fetchall()]

    # 7.3) Prateleiras que tiveram evento de entrada
    cursor.execute(
        "SELECT DISTINCT prateleira FROM Eventos "
        "WHERE evento='entrada' AND prateleira<>'Fora da prateleira';"
    )
    rows = cursor.fetchall()
    prateleiras = sorted(
        [r['prateleira'] for r in rows if r['prateleira'].startswith('Prateleira ')],
        key=lambda s: int(s.split()[-1])
    )

    # 7.4) Monta lista de prateleiras + objetos (últimas 24h, último evento 'entrada')
    shelves = []
    for prat in prateleiras:
        base_query = (
            "SELECT e.track_id, e.objeto, e.posicao "
            "FROM Eventos e "
            "JOIN ("
            "   SELECT track_id, MAX(timestamp) AS maxt "
            "   FROM Eventos GROUP BY track_id"
            ") m ON e.track_id = m.track_id AND e.timestamp = m.maxt "
            "WHERE e.evento = 'entrada' "
            "  AND e.prateleira = %s "
            "  AND m.maxt >= NOW() - INTERVAL 1 DAY"
        )
        params = [prat]
        if classes_filtro:
            placeholder = ','.join(['%s'] * len(classes_filtro))
            base_query += f" AND e.objeto IN ({placeholder})"
            params.extend(classes_filtro)

        cursor.execute(base_query, params)
        objs = []
        for o in cursor.fetchall():
            cursor.execute(
                "SELECT x, y FROM Detecoes WHERE track_id=%s ORDER BY timestamp DESC LIMIT 1;",
                (o['track_id'],)
            )
            pos = cursor.fetchone() or {'x': 0, 'y': 0}
            objs.append({
                'name':     o['objeto'],
                'position': o['posicao'],
                'pos_x':    pos['x'],
                'pos_y':    pos['y']
            })
        shelves.append({'id': prat.split()[-1], 'objects': objs})

    # 7.5) Objetos “fora” (último evento = 'saída' ou prateleira = 'Fora da prateleira')
    cursor.execute(
        "SELECT e.track_id, e.objeto, e.posicao "
        "FROM Eventos e "
        "JOIN ("
        "   SELECT track_id, MAX(timestamp) AS maxt "
        "   FROM Eventos GROUP BY track_id"
        ") m ON e.track_id = m.track_id AND e.timestamp = m.maxt "
        "WHERE e.evento = 'saída' OR e.prateleira = 'Fora da prateleira';"
    )
    outside_objects = []
    for o in cursor.fetchall():
        cursor.execute(
            "SELECT x, y FROM Detecoes WHERE track_id=%s ORDER BY timestamp DESC LIMIT 1;",
            (o['track_id'],)
        )
        pos = cursor.fetchone() or {'x': 0, 'y': 0}
        outside_objects.append({
            'name':     o['objeto'],
            'position': o['posicao'],
            'pos_x':    pos['x'],
            'pos_y':    pos['y']
        })

    # 7.6) Entradas por prateleira (Gráfico Doughnut)
    query1 = "SELECT prateleira, COUNT(*) AS total_entradas FROM Eventos WHERE evento='entrada'"
    params1 = []
    if prateleira_filtro:
        query1 += " AND prateleira = %s"; params1.append(prateleira_filtro)
    query1 += " GROUP BY prateleira;"
    cursor.execute(query1, params1)
    entradas_por_prateleira = cursor.fetchall()

    # 7.7) Eventos por data (Gráfico de barras)
    query2 = "SELECT DATE(timestamp) AS data, COUNT(*) AS total_eventos FROM Eventos WHERE 1=1"
    params2 = []
    if data_inicial:
        query2 += " AND timestamp >= %s"; params2.append(data_inicial)
    if data_final:
        query2 += " AND timestamp <= %s"; params2.append(data_final)
    query2 += " GROUP BY DATE(timestamp) ORDER BY data;"
    cursor.execute(query2, params2)
    eventos_por_data = cursor.fetchall()

    # 7.8) Últimos 10 eventos (Tabela)
    query3 = "SELECT track_id, objeto, prateleira, posicao, evento, timestamp FROM Eventos"
    filters = []
    params3 = []
    if data_inicial:
        filters.append("timestamp >= %s"); params3.append(data_inicial)
    if data_final:
        filters.append("timestamp <= %s"); params3.append(data_final)
    if prateleira_filtro:
        filters.append("prateleira = %s"); params3.append(prateleira_filtro)
    if classes_filtro:
        placeholder3 = ','.join(['%s'] * len(classes_filtro))
        filters.append(f"objeto IN ({placeholder3})"); params3.extend(classes_filtro)
    if filters:
        query3 += " WHERE " + " AND ".join(filters)
    query3 += " ORDER BY timestamp DESC LIMIT 10;"
    cursor.execute(query3, params3)
    eventos_recentes = cursor.fetchall()

    # 7.9) Total de eventos
    query4 = "SELECT COUNT(*) AS total_eventos FROM Eventos WHERE 1=1"
    params4 = []
    if data_inicial:
        query4 += " AND timestamp >= %s"; params4.append(data_inicial)
    if data_final:
        query4 += " AND timestamp <= %s"; params4.append(data_final)
    if prateleira_filtro:
        query4 += " AND prateleira = %s"; params4.append(prateleira_filtro)
    if classes_filtro:
        placeholder4 = ','.join(['%s'] * len(classes_filtro))
        query4 += f" AND objeto IN ({placeholder4})"; params4.extend(classes_filtro)
    cursor.execute(query4, params4)
    total_eventos = cursor.fetchone()['total_eventos']

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        user=current_user.username,
        shelves=shelves,
        outside_objects=outside_objects,
        entradas=entradas_por_prateleira,
        eventos=eventos_por_data,
        recentes=eventos_recentes,
        total_eventos=total_eventos,
        data_inicial=data_inicial or '',
        data_final=data_final or '',
        prateleira_filtro=prateleira_filtro or '',
        all_classes=all_classes,
        classes_filtro=classes_filtro
    )

# ----------------------------
# 8) SOCKET.IO: emitir eventos em tempo real
# ----------------------------
@socketio.on('new_event')
def handle_new_event(data):
    socketio.emit('new_event', data)

# ----------------------------
# 9) EXPORT CSV
# ----------------------------
@app.route('/export', methods=['GET'])
@login_required
def export_csv():
    data_inicial      = request.args.get('data_inicial')
    data_final        = request.args.get('data_final')
    prateleira_filtro = request.args.get('prateleira')
    classes_filtro    = request.args.getlist('classe')

    conn = get_connection()
    if not conn:
        return 'Erro na conexão com o banco de dados.', 500
    cursor = conn.cursor(dictionary=True)

    # Monta a query conforme filtros
    query = "SELECT track_id, objeto, prateleira, posicao, evento, timestamp FROM Eventos WHERE 1=1"
    params = []
    if data_inicial:
        query += " AND timestamp >= %s"; params.append(data_inicial)
    if data_final:
        query += " AND timestamp <= %s"; params.append(data_final)
    if prateleira_filtro:
        query += " AND prateleira = %s"; params.append(prateleira_filtro)
    if classes_filtro:
        placeholder = ','.join(['%s'] * len(classes_filtro))
        query += f" AND objeto IN ({placeholder})"; params.extend(classes_filtro)

    query += " ORDER BY timestamp DESC;"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Gera CSV na memória
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['track_id', 'objeto', 'prateleira', 'posicao', 'evento', 'timestamp'])
    for r in rows:
        writer.writerow([
            r['track_id'],
            r['objeto'],
            r['prateleira'],
            r['posicao'],
            r['evento'],
            r['timestamp']
        ])
    output = si.getvalue()
    si.close()

    response = Response(output, mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='eventos_export.csv')
    return response

# ----------------------------
# 10) FUNÇÃO DE LIMPEZA AO INICIAR (não chamada automaticamente)
# ----------------------------
def clear_ongoing_entries():
    """
    Insere eventos de 'saída' para todos os track_id cujo último evento foi 'entrada',
    evitando que objetos fiquem 'presos' de execução anterior.
    """
    conn = get_connection()
    if not conn:
        print("Não foi possível conectar ao BD para limpar entradas pendentes.")
        return

    cursor = conn.cursor(dictionary=True)
    # Seleciona todos cujos últimos eventos são 'entrada'
    cursor.execute(
        """
        SELECT e.track_id, e.objeto
        FROM Eventos e
        JOIN (
            SELECT track_id, MAX(timestamp) AS maxt
            FROM Eventos
            GROUP BY track_id
        ) m ON e.track_id = m.track_id AND e.timestamp = m.maxt
        WHERE e.evento = 'entrada';
        """
    )
    rows = cursor.fetchall()
    if not rows:
        cursor.close()
        conn.close()
        return

    # Insere evento de saída para cada um
    for r in rows:
        cursor.execute(
            """
            INSERT INTO Eventos (track_id, objeto, prateleira, posicao, evento, timestamp)
            VALUES (%s, %s, %s, %s, %s, NOW());
            """,
            (r['track_id'], r['objeto'], 'Fora da prateleira', None, 'saída')
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Limpeza (não automática): inseridos {len(rows)} eventos de saída para entradas pendentes.")

# ----------------------------
# 11) PONTO DE ENTRADA
# ----------------------------
if __name__ == '__main__':
    init_users_table()
    # OBS: não chamamos clear_ongoing_entries() aqui para não limpar automaticamente
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
