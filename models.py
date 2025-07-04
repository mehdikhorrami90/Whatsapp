from enum import unique

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from flask_login import UserMixin  # Don't forget this!
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

db = SQLAlchemy()


class User(db.Model, UserMixin):  # Add UserMixin here
    __tablename__ = 'users'  # Add this to match your foreign key

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    contacts = db.relationship('Contact', backref='owner', lazy=True, cascade='all, delete-orphan')

    # Flask-Login required properties (UserMixin provides these, but explicit is good)
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __init__(self, username, password=None):
        self.username = username
        if password:
            self.set_password(password)

    def set_password(self, password):
        """Create hashed password with validation"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    contact_name = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint('user_id', 'contact_name', name='unique_contact_per_user'),
    )

    def __repr__(self):
        return f'<Contact {self.contact_name} of user {self.user_id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        db.Index('ix_message_room', 'room'),
        db.Index('ix_message_timestamp', 'timestamp'),
    )
    def to_dict(self):
        return {
            'username': self.username,
            'message': self.content,
            'timestamp': self.timestamp.isoformat()
        }

# In models.py - make sure these table names are consistent
class Room(db.Model):
    __tablename__ = 'rooms'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    # ... rest of the model

# Association table should reference the explicit table names
room_members = db.Table('room_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('room_id', db.Integer, db.ForeignKey('rooms.id'))  # Changed from 'room.id' to 'rooms.id'
)