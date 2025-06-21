from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from werkzeug.utils import redirect

from contacts import bp as contacts_bp  # 🔗 import Blueprint
import auth

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Track user sessions by socket ID
user_data = {}

#Add a secret key
app.secret_key = "super_secret_key"  # for session handling

# Register the contacts blueprint
app.register_blueprint(contacts_bp)


@app.route('/')
def index():
    if not session.get('username'):
        return redirect('/login')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def handle_auth():
    username = request.form['username']
    password = request.form['password']
    action = request.form['action']

    if action == 'Register':
        success = auth.register_user(username, password)
        if not success:
            return "Username already exists. Go back and try again."
    elif action == 'Login':
        success = auth.login_user(username, password)
        if not success:
            return "Invalid login. Go back and try again."
    session['username'] = username
    return redirect("/chat")

@app.route('/chat')
def chat_page():
    if "username" not in session:
        return redirect("/")
    return render_template("index.html", username=session["username"])


@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    user_data[request.sid] = {'username': username, 'room': room}
    join_room(room)
    send(f"{username} has joined room {room}", room=room)
    emit('joined')
    print(f"[DEBUG] handle_join received: {data}")


@socketio.on('send_message')
def handle_send_message(msg):
    user = user_data.get(request.sid)
    if not user:
        return
    username = user['username']
    room = user['room']
    send(f"{username}: {msg}", room=room)


@socketio.on('disconnect')
def handle_disconnect():
    user = user_data.pop(request.sid, {})
    username = user.get('username', 'Unknown')
    room = user.get('room')
    if room:
        send(f"{username} has left the room.", room=room)


if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False)
#This is the first change