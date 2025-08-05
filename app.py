import datetime

from flask import Flask, render_template, request, session, redirect, flash, jsonify
from flask.sansio.blueprints import Blueprint
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from contacts import bp as contacts_bp  # Contacts Blueprint
import auth
from models import db, User, Message  # SQLAlchemy db instance from models.py
from sqlalchemy.orm import Session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Register Blueprints
app.register_blueprint(contacts_bp, url_prefix='/contacts')

csrf = CSRFProtect(app)

# Track user sessions by socket ID
user_data = {}

bp = Blueprint('contacts', __name__)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

# Create database tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    if not session.get('username'):
        return redirect('/login')
    return redirect('/chat')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def handle_auth():
    username = request.form['username']
    password = request.form['password']
    action = request.form['action']

    if action == 'Register':
        if not auth.register_user(username, password):
            flash('Username already exists')
            return redirect('/login')
        # After successful registration, automatically log the user in
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        login_user(user)
        session['username'] = username
        return redirect('/chat')
    elif action == 'Login':
        user = auth.login_user(username, password)
        if not user:
            flash('Invalid username or password')
            return redirect('/login')
        login_user(user)
        session['username'] = username
        return redirect('/chat')

    return redirect('/login')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('username', None)
    return redirect('/login')

@app.route('/chat')
@login_required
def chat_page():
    return render_template("index.html", username=session["username"])

@app.route('/api/rooms/messages')
@login_required
def get_room_messages():
    room_name = request.args.get('room', 'general')
    messages = Message.query.filter_by(room=room_name)\
                  .order_by(Message.timestamp.asc())\
                  .all()
    return jsonify([m.to_dict() for m in messages])

# SocketIO Events
@socketio.on('join')
def handle_join(data):
    if not current_user.is_authenticated:
        return
    username = data.get('username')
    room = data.get('room')

    if not username or not room:
        return

    user_data[request.sid] = {'username': username, 'room': room}
    join_room(room)

    # Send existing messages first
    emit('message_history', get_room_history(room))

    # Then notify others about the join
    send(f"{username} has joined room {room}", room=room)
    emit('joined')


@socketio.on('send_message')
def handle_send_message(data):
    user = user_data.get(request.sid)
    if not user:
        return

    username = user['username']
    room = user['room']
    message = data.get('message', '').strip()

    if not message:  # Don't process empty messages
        return

    # Save to database (only one method needed)
    try:
        # Modern SQLAlchemy 2.0 style insertion
        with db.session.begin():
            msg = Message(
                room=room,
                username=username,
                content=message
            )
            db.session.add(msg)
    except Exception as e:
        print(f"Error saving message: {e}")
        return

    emit('message', {
        'username': username,
        'message': message,
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat()
    }, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    user = user_data.pop(request.sid, {})
    username = user.get('username', 'Unknown')
    room = user.get('room')
    if room:
        send(f"{username} has left the room.", room=room)

# Message storage functions
def save_message(room, username, message):
    msg = Message(room=room, username=username, content=message)
    db.session.add(msg)
    db.session.commit()

def get_room_history(room, limit=50):
    messages = Message.query.filter_by(room=room)\
                 .order_by(Message.timestamp.desc())\
                 .limit(limit)\
                 .all()
    return [msg.to_dict() for msg in reversed(messages)]  # Return in chronological order

# Update the join_room handler to properly track room membership
@socketio.on('join_room')
def handle_join_room(data):
    if not current_user.is_authenticated:
        return

    room = data.get('room', 'general')
    username = data.get('username')

    # Update user's current room
    if request.sid in user_data:
        user_data[request.sid]['room'] = room

    join_room(room)
    emit('message_history', get_room_history(room))

    # Notify others
    emit('message', {
        'username': 'System',
        'message': f'{username} has joined the room',
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat()
    }, room=room)


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0", port=5001, use_reloader=False)
