from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    history = db.relationship('History', backref='user', lazy=True)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    input_type = db.Column(db.String(50), nullable=False) # 'text', 'url', 'pdf'
    input_content = db.Column(db.Text, nullable=False) # Store snippet or full text
    prediction = db.Column(db.String(50), nullable=False) # 'Fake' or 'True'
    confidence = db.Column(db.Float, nullable=False) # E.g., 0.95
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
