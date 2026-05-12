from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# --------------------- Пользователи и роли ---------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # customer, driver, admin

    # Связи
    driver_profile = db.relationship('Driver', backref='user', uselist=False, cascade='all, delete-orphan')
    orders_as_customer = db.relationship('Order', backref='customer', foreign_keys='Order.customer_id', lazy='dynamic')
    orders_as_driver = db.relationship('Order', backref='driver', foreign_keys='Order.driver_id', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --------------------- Водитель ---------------------
class Driver(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    car_info = db.Column(db.String(100))
    license_number = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)


# --------------------- Тариф ---------------------
class Tariff(db.Model):
    __tablename__ = 'tariffs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    base_fare = db.Column(db.Float, nullable=False, default=0)
    price_per_km = db.Column(db.Float, nullable=False, default=0)


# --------------------- Заказ ---------------------
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariffs.id'), nullable=False)

    pickup_address = db.Column(db.String(200), nullable=False)
    dropoff_address = db.Column(db.String(200), nullable=False)
    pickup_lat = db.Column(db.Float)
    pickup_lon = db.Column(db.Float)
    dropoff_lat = db.Column(db.Float)
    dropoff_lon = db.Column(db.Float)
    distance_km = db.Column(db.Float)
    cost = db.Column(db.Float)

    status = db.Column(db.String(20), default='pending')  # pending, assigned, accepted, in_progress, completed, cancelled, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    tariff = db.relationship('Tariff', backref='orders')
    status_logs = db.relationship('OrderStatusLog', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='order', uselist=False)


# --------------------- Лог статусов ---------------------
class OrderStatusLog(db.Model):
    __tablename__ = 'order_status_logs'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# --------------------- Платёж ---------------------
class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='unpaid')  # unpaid/paid
    paid_at = db.Column(db.DateTime, nullable=True)