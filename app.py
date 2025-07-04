import datetime
from flask import Flask, render_template, request, session, redirect, flash, url_for, jsonify
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from contacts import bp as contacts_bp
import auth
from models import db, User, Message, Room
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")  # Add CORS for SocketIO
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Register Blueprints
app.register_blueprint(contacts_bp)

csrf = CSRFProtect(app)

# Track user sessions by socket ID
user_data = {}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


# Create database tables
with app.app_context():
    db.drop_all()
    db.create_all()


# Routes
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('list_rooms'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('list_rooms'))
    return render_template('login.html')


@app.route('/auth', methods=['POST'])
def handle_auth():
    username = request.form['username']
    password = request.form['password']
    action = request.form['action']

    if action == 'Register':
        user = auth.register_user(username, password)
        if not user:
            flash('Username already exists or invalid credentials')
            return redirect(url_for('login'))
        login_user(user)
        session['username'] = username
        return redirect(url_for('list_rooms'))
    elif action == 'Login':
        user = auth.login_user(username, password)
        if not user:
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        session['username'] = username
        return redirect(url_for('list_rooms'))

    return redirect(url_for('login'))


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/chat')
@login_required
def chat_page():
    return render_template("index.html", username=current_user.username)


# Room Management
@app.route('/rooms')
@login_required
def list_rooms():
    rooms = current_user.rooms  # Only show rooms the user is a member of
    return render_template("rooms.html", rooms=rooms, current_room=None)


@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    room_name = request.form.get('room_name', '').strip()
    if not room_name:
        flash('Room name cannot be empty')
        return redirect(url_for('list_rooms'))

    try:
        new_room = Room(name=room_name, creator_id=current_user.id)
        new_room.members.append(current_user)
        db.session.add(new_room)
        db.session.commit()
        flash('Room created successfully')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('Error creating room - name may already exist')

    return redirect(url_for('list_rooms'))


@app.route('/room/<int:room_id>')
@login_required
def chat_room(room_id):
    room = Room.query.get_or_404(room_id)
    if current_user not in room.members:
        flash("You don't have access to this room")
        return redirect(url_for('list_rooms'))
    return render_template('rooms.html', rooms=current_user.rooms, current_room=room)


# API Endpoints
@app.route('/api/rooms/<int:room_id>/messages')
@login_required
def get_room_messages(room_id):
    room = Room.query.get_or_404(room_id)
    if current_user not in room.members:
        return jsonify({'error': 'Unauthorized'}), 403

    messages = Message.query.filter_by(room_id=room_id) \
        .order_by(Message.timestamp.asc()) \
        .all()
    return jsonify([m.to_dict() for m in messages])


# SocketIO Events
@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False  # Reject connection


@socketio.on('join_room')
def handle_join_room(data):
    if not current_user.is_authenticated:
        return

    room_id = data.get('room')
    if not room_id:
        return

    room = Room.query.get(room_id)
    if not room or current_user not in room.members:
        emit('error', {'message': 'Room not found or access denied'})
        return

    join_room(str(room_id))  # Convert to string for consistency
    user_data[request.sid] = {
        'username': current_user.username,
        'room': room_id,
        'user_id': current_user.id
    }

    # Send room info and history
    messages = Message.query.filter_by(room_id=room_id) \
        .order_by(Message.timestamp.asc()) \
        .limit(100) \
        .all()

    emit('room_info', {
        'room_id': room.id,
        'room_name': room.name,
        'creator_id': room.creator_id,
        'members': [m.username for m in room.members]
    })

    emit('message_history', [m.to_dict() for m in messages])

    # Notify others
    emit('message', {
        'username': 'System',
        'message': f'{current_user.username} has joined the room',
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
        'system': True
    }, room=str(room_id))


@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('room')
    if not room_id:
        return

    leave_room(str(room_id))
    user_info = user_data.pop(request.sid, {})

    if user_info:
        emit('message', {
            'username': 'System',
            'message': f'{user_info.get("username", "Someone")} has left the room',
            'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
            'system': True
        }, room=str(room_id))


@socketio.on('send_message')
def handle_send_message(data):
    user_info = user_data.get(request.sid)
    if not user_info or not current_user.is_authenticated:
        return

    room_id = user_info.get('room')
    message = data.get('message', '').strip()
    if not room_id or not message:
        return

    try:
        msg = Message(
            room_id=room_id,
            username=current_user.username,
            user_id=current_user.id,
            content=message
        )
        db.session.add(msg)
        db.session.commit()

        emit('message', msg.to_dict(), room=str(room_id))
    except SQLAlchemyError as e:
        db.session.rollback()
        emit('error', {'message': 'Failed to save message'})


@socketio.on('disconnect')
def handle_disconnect():
    user_info = user_data.pop(request.sid, {})
    if user_info:
        room_id = user_info.get('room')
        if room_id:
            emit('message', {
                'username': 'System',
                'message': f'{user_info.get("username", "Someone")} has disconnected',
                'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
                'system': True
            }, room=str(room_id))


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0", port=5001)