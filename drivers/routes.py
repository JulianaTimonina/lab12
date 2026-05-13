from flask import Blueprint, request, jsonify
from models import db, User, Order
from decorators import admin_required

drivers_bp = Blueprint('drivers', __name__, url_prefix='/drivers')

@drivers_bp.route('', methods=['GET'])
@admin_required
def list_drivers():
    drivers = User.query.filter_by(role='driver').all()
    return jsonify([driver.to_dict() for driver in drivers]), 200

@drivers_bp.route('', methods=['POST'])
@admin_required
def create_driver():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'msg': 'Missing required fields'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'msg': 'Email already exists'}), 409

    driver = User(
        email=data['email'],
        name=data['name'],
        phone=data.get('phone', ''),
        role='driver',
        vehicle=data.get('vehicle', ''),
        is_available=data.get('is_available', True)
    )
    driver.set_password(data['password'])
    db.session.add(driver)
    db.session.commit()
    return jsonify(driver.to_dict()), 201

@drivers_bp.route('/<int:driver_id>', methods=['PUT'])
@admin_required
def update_driver(driver_id):
    driver = db.session.get(User, driver_id)
    if driver is None or driver.role != 'driver':
        return jsonify({'msg': 'Driver not found'}), 404

    data = request.get_json()
    if 'name' in data: driver.name = data['name']
    if 'phone' in data: driver.phone = data['phone']
    if 'vehicle' in data: driver.vehicle = data['vehicle']
    if 'is_available' in data: driver.is_available = data['is_available']
    if 'password' in data and data['password']:
        driver.set_password(data['password'])

    db.session.commit()
    return jsonify(driver.to_dict()), 200

@drivers_bp.route('/<int:driver_id>', methods=['DELETE'])
@admin_required
def delete_driver(driver_id):
    driver = db.session.get(User, driver_id)
    if driver is None or driver.role != 'driver':
        return jsonify({'msg': 'Driver not found'}), 404

    # Проверяем, есть ли у водителя активные заказы
    active_statuses = ['pending', 'assigned', 'accepted', 'in_progress']
    active_orders = Order.query.filter(
        Order.driver_id == driver_id,
        Order.status.in_(active_statuses)
    ).count()
    if active_orders > 0:
        return jsonify({'msg': 'Cannot delete driver with active orders'}), 400

    db.session.delete(driver)
    db.session.commit()
    return jsonify({'msg': 'Driver deleted'}), 200

@drivers_bp.route('/available', methods=['GET'])
@admin_required
def available_drivers():
    drivers = User.query.filter_by(role='driver', is_available=True).all()
    return jsonify([driver.to_dict() for driver in drivers]), 200