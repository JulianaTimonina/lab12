from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # 'customer', 'driver', 'admin'
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    vehicle = db.Column(db.String(100))
    is_available = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'phone': self.phone,
            'vehicle': self.vehicle,
            'is_available': self.is_available
        }

class Tariff(db.Model):
    __tablename__ = 'tariffs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    base_fee = db.Column(db.Float, nullable=False, default=0.0)
    price_per_km = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    description = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'base_fee': self.base_fee,
            'price_per_km': self.price_per_km,
            'currency': self.currency,
            'description': self.description
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariffs.id'), nullable=False)
    pickup_address = db.Column(db.String(255), nullable=False)
    destination_address = db.Column(db.String(255), nullable=False)
    pickup_lat = db.Column(db.Float)
    pickup_lon = db.Column(db.Float)
    dest_lat = db.Column(db.Float)
    dest_lon = db.Column(db.Float)
    distance_km = db.Column(db.Float)
    cost = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')  # pending, assigned, accepted, in_progress, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_orders')
    driver = db.relationship('User', foreign_keys=[driver_id], backref='driver_orders')
    tariff = db.relationship('Tariff', backref='orders')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'driver_id': self.driver_id,
            'tariff_id': self.tariff_id,
            'pickup_address': self.pickup_address,
            'destination_address': self.destination_address,
            'pickup_lat': self.pickup_lat,
            'pickup_lon': self.pickup_lon,
            'dest_lat': self.dest_lat,
            'dest_lon': self.dest_lon,
            'distance_km': self.distance_km,
            'cost': self.cost,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'customer_name': self.customer.name if self.customer else None,
            'driver_name': self.driver.name if self.driver else None,
            'tariff_name': self.tariff.name if self.tariff else None
        }