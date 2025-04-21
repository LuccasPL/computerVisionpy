from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
socketio = SocketIO(app, cors_allowed_origins='*')

# Configuração do Login Manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Configuração do BD
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

# Modelo de Usuário
class User(UserMixin):
    def __init__(self, id_, username, password_hash):
        self.id = id_
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, password_hash FROM Usuarios WHERE id=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    if row:
        return User(row['id'], row['username'], row['password_hash'])
    return None

# Inicializa tabela de usuários
def init_users_table():
    conn = get_connection()
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
    cursor.close(); conn.close()

# Registro
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hash_ = generate_password_hash(password)
        conn = get_connection(); cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Usuarios (username, password_hash) VALUES (%s,%s)", (username, hash_))
            conn.commit()
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Error:
            flash('Username já existe.', 'danger')
        finally:
            cursor.close(); conn.close()
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM Usuarios WHERE username=%s", (username,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['password_hash'])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login inválido.', 'danger')
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# API histórico
@app.route('/api/prateleira/<int:prat_id>/history')
@login_required
def shelf_history(prat_id):
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT track_id, objeto, evento, timestamp
        FROM Eventos
        WHERE prateleira = %s
        ORDER BY timestamp DESC
        """,
        (f'Prateleira {prat_id}',)
    )
    history = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(history=history)

# Dashboard
@app.route('/', methods=['GET'])
@login_required
def dashboard():
    # filtros
    data_inicial = request.args.get('data_inicial')
    data_final   = request.args.get('data_final')
    prateleira_filtro = request.args.get('prateleira')
    classes_filtro    = request.args.getlist('classe')

    conn = get_connection()
    if not conn:
        return 'Erro na conexão com o banco de dados.'
    cursor = conn.cursor(dictionary=True)

    # classes disponíveis
    cursor.execute("SELECT DISTINCT objeto FROM Eventos")
    all_classes = [r['objeto'] for r in cursor.fetchall()]

    # visão geral prateleiras
    cursor.execute(
        "SELECT DISTINCT prateleira FROM Eventos "
        "WHERE evento='entrada' AND prateleira<>'Fora da prateleira';"
    )
    rows = cursor.fetchall()
    prateleiras = sorted([r['prateleira'] for r in rows], key=lambda s:int(s.split()[-1]))
    shelves = []
    for prat in prateleiras:
        q = (
            "SELECT e.track_id, e.objeto FROM Eventos e "
            "JOIN (SELECT track_id, MAX(timestamp) AS maxt FROM Eventos GROUP BY track_id) m "
            "ON e.track_id=m.track_id AND e.timestamp=m.maxt "
            "WHERE e.evento='entrada' AND e.prateleira=%s"
        )
        params = [prat]
        if classes_filtro:
            ph = ','.join(['%s']*len(classes_filtro))
            q += f" AND e.objeto IN ({ph})"
            params += classes_filtro
        cursor.execute(q, params)
        objs=[]
        for o in cursor.fetchall():
            cursor.execute(
                "SELECT x,y FROM Detecoes WHERE track_id=%s ORDER BY timestamp DESC LIMIT 1;",
                (o['track_id'],)
            )
            pos = cursor.fetchone() or {'x':0,'y':0}
            objs.append({'name':o['objeto'],'pos_x':pos['x'],'pos_y':pos['y']})
        shelves.append({'id':prat.split()[-1],'objects':objs})

    # objetos fora
    cursor.execute(
        "SELECT e.track_id,e.objeto FROM Eventos e "
        "JOIN (SELECT track_id,MAX(timestamp) AS maxt FROM Eventos GROUP BY track_id) m "
        "ON e.track_id=m.track_id AND e.timestamp=m.maxt "
        "WHERE e.evento='saída' OR e.prateleira='Fora da prateleira';"
    )
    outside_objects=[]
    for o in cursor.fetchall():
        cursor.execute(
            "SELECT x,y FROM Detecoes WHERE track_id=%s ORDER BY timestamp DESC LIMIT 1;",
            (o['track_id'],)
        )
        pos = cursor.fetchone() or {'x':0,'y':0}
        outside_objects.append({'name':o['objeto'],'pos_x':pos['x'],'pos_y':pos['y']})

    # Entradas por prateleira
    query1 = "SELECT prateleira, COUNT(*) AS total_entradas FROM Eventos WHERE evento='entrada'"
    params=[]
    if prateleira_filtro:
        query1 += " AND prateleira=%s"; params.append(prateleira_filtro)
    query1 += " GROUP BY prateleira;"; cursor.execute(query1, params)
    entradas_por_prateleira = cursor.fetchall()

    # Eventos por data
    query2 = "SELECT DATE(timestamp) AS data, COUNT(*) AS total_eventos FROM Eventos WHERE 1=1"
    params=[]
    if data_inicial:
        query2 += " AND timestamp>=%s"; params.append(data_inicial)
    if data_final:
        query2 += " AND timestamp<=%s"; params.append(data_final)
    query2 += " GROUP BY DATE(timestamp) ORDER BY data;"; cursor.execute(query2, params)
    eventos_por_data = cursor.fetchall()

    # Eventos recentes
    query3 = "SELECT track_id,objeto,prateleira,evento,timestamp FROM Eventos"
    filters=[]; params=[]
    if data_inicial: filters.append("timestamp>=%s"); params.append(data_inicial)
    if data_final: filters.append("timestamp<=%s"); params.append(data_final)
    if prateleira_filtro: filters.append("prateleira=%s"); params.append(prateleira_filtro)
    if filters: query3 += " WHERE " + " AND ".join(filters)
    query3 += " ORDER BY timestamp DESC LIMIT 10;"; cursor.execute(query3, params)
    eventos_recentes = cursor.fetchall()

    # Total de eventos
    query4 = "SELECT COUNT(*) AS total_eventos FROM Eventos WHERE 1=1"
    params=[]
    if data_inicial: query4 += " AND timestamp>=%s"; params.append(data_inicial)
    if data_final: query4 += " AND timestamp<=%s"; params.append(data_final)
    cursor.execute(query4, params)
    total_eventos = cursor.fetchone()['total_eventos']

    cursor.close(); conn.close()
    return render_template(
        'dashboard.html',
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
        classes_filtro=classes_filtro,
        user=current_user.username
    )

@socketio.on('new_event')
def handle_new_event(data):
    socketio.emit('new_event', data)

@app.route('/export')
@login_required
def export_csv():
    # implementação permanece igual
    ...

if __name__ == '__main__':
    init_users_table()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
