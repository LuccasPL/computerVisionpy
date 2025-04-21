import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = 'admin'
socketio = SocketIO(app, cors_allowed_origins='*')

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '78517231Le!',
    'database': 'deteccoes_db'
}

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
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, password_hash FROM Usuarios WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return User(row['id'], row['username'], row['password_hash'])
    return None


def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print("DB connection error:", e)
        return None

@app.before_first_request
def init_tables():
    conn = get_connection()
    cursor = conn.cursor()
    # Tabela de usuários
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS Usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(150) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        );''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cursor = conn.cursor()
        hash_ = generate_password_hash(password)
        try:
            cursor.execute("INSERT INTO Usuarios (username, password_hash) VALUES (%s, %s)", (username, hash_))
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
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM Usuarios WHERE username=%s", (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['password_hash'])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login inválido.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
@login_required
def dashboard():
    # Aqui coloque o código que antes existia em 'index()' do dashboard.py
    # ... carrega dados de prateleiras, objetos e renderiza 'dashboard.html' ...
    return render_template('dashboard.html', **locals())

@socketio.on('new_event')
def handle_new_event(data):
    socketio.emit('new_event', data)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
