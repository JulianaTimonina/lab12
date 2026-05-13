from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, User, Order, Tariff
from geocoding.utils import get_coordinates, calculate_distance
from decorators import admin_required

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('', methods=['POST'])
@jwt_required()
def create_order():
    claims = get_jwt()
    if claims.get('role') != 'customer':
        return jsonify({'msg': 'Only customers can create orders'}), 403

    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not all(k in data for k in ('pickup_address', 'destination_address', 'tariff_id')):
        return jsonify({'msg': 'Missing required fields'}), 400

    try:
        pickup_lat, pickup_lon = get_coordinates(data['pickup_address'])
        dest_lat, dest_lon = get_coordinates(data['destination_address'])
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400

    distance_km = calculate_distance(pickup_lat, pickup_lon, dest_lat, dest_lon)

    tariff = db.session.get(Tariff, data['tariff_id'])
    if tariff is None:
        return jsonify({'msg': 'Tariff not found'}), 404

    cost = round(tariff.base_fee + distance_km * tariff.price_per_km, 2)

    order = Order(
        customer_id=user_id,
        tariff_id=tariff.id,
        pickup_address=data['pickup_address'],
        destination_address=data['destination_address'],
        pickup_lat=pickup_lat,
        pickup_lon=pickup_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        distance_km=round(distance_km, 2),
        cost=cost,
        status='pending'
    )
    db.session.add(order)
    db.session.commit()

    return jsonify(order.to_dict()), 201

@orders_bp.route('', methods=['GET'])
@jwt_required()
def get_orders():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    role = claims.get('role')

    if role == 'admin':
        orders = Order.query.order_by(Order.created_at.desc()).all()
    elif role == 'customer':
        orders = Order.query.filter_by(customer_id=user_id).order_by(Order.created_at.desc()).all()
    elif role == 'driver':
        # Водитель видит все свободные заказы (pending без водителя) + свой активный заказ (если есть)
        pending_orders = Order.query.filter(
            Order.status == 'pending',
            Order.driver_id.is_(None)
        ).order_by(Order.created_at.desc()).all()

        active_order = Order.query.filter(
            Order.driver_id == user_id,
            Order.status.in_(['assigned', 'accepted', 'in_progress'])
        ).first()

        # Объединяем: сначала активный (если есть), потом свободные
        result = []
        if active_order:
            result.append(active_order)
        result.extend(pending_orders)
        return jsonify([o.to_dict() for o in result]), 200
    else:
        return jsonify({'msg': 'Invalid role'}), 403

    return jsonify([order.to_dict() for order in orders]), 200

@orders_bp.route('/<int:order_id>/assign', methods=['PATCH'])
@admin_required
def assign_driver(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({'msg': 'Order not found'}), 404
    if order.status != 'pending':
        return jsonify({'msg': 'Order can only be assigned when pending'}), 400

    data = request.get_json()
    driver_id = data.get('driver_id')
    if not driver_id:
        return jsonify({'msg': 'driver_id is required'}), 400

    driver = db.session.get(User, driver_id)
    if not driver or driver.role != 'driver':
        return jsonify({'msg': 'Invalid driver'}), 400
    if not driver.is_available:
        return jsonify({'msg': 'Driver is not available'}), 400

    order.driver_id = driver_id
    order.status = 'assigned'
    driver.is_available = False   # водитель теперь занят
    db.session.commit()
    return jsonify(order.to_dict()), 200

# --- Новый эндпоинт: водитель берёт заказ сам ---
@orders_bp.route('/<int:order_id>/take', methods=['PATCH'])
@jwt_required()
def take_order(order_id):
    """Водитель назначает себя на свободный заказ"""
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return jsonify({'msg': 'Only drivers can take orders'}), 403

    driver_id = int(get_jwt_identity())
    driver = db.session.get(User, driver_id)
    if not driver or driver.role != 'driver':
        return jsonify({'msg': 'Invalid driver'}), 400

    # Проверяем, нет ли уже активного заказа
    active_order = Order.query.filter(
        Order.driver_id == driver_id,
        Order.status.in_(['assigned', 'accepted', 'in_progress'])
    ).first()
    if active_order:
        return jsonify({'msg': 'You already have an active order. Complete it before taking a new one.'}), 400

    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({'msg': 'Order not found'}), 404
    if order.status != 'pending' or order.driver_id is not None:
        return jsonify({'msg': 'Order is already taken or not pending'}), 400

    if not driver.is_available:
        return jsonify({'msg': 'You are not available'}), 400

    order.driver_id = driver_id
    order.status = 'assigned'
    driver.is_available = False
    db.session.commit()
    return jsonify(order.to_dict()), 200

@orders_bp.route('/<int:order_id>/accept', methods=['PATCH'])
@jwt_required()
def accept_order(order_id):
    """Водитель принимает заказ"""
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return jsonify({'msg': 'Only drivers can accept orders'}), 403

    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({'msg': 'Order not found'}), 404
    if order.driver_id != user_id:
        return jsonify({'msg': 'You are not assigned to this order'}), 403
    if order.status != 'assigned':
        return jsonify({'msg': f'Cannot accept order in status {order.status}'}), 400

    order.status = 'accepted'
    db.session.commit()
    return jsonify(order.to_dict()), 200

@orders_bp.route('/<int:order_id>/start', methods=['PATCH'])
@jwt_required()
def start_order(order_id):
    """Водитель начинает поездку"""
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return jsonify({'msg': 'Only drivers can start orders'}), 403

    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({'msg': 'Order not found'}), 404
    if order.driver_id != user_id:
        return jsonify({'msg': 'You are not assigned to this order'}), 403
    if order.status != 'accepted':
        return jsonify({'msg': f'Cannot start order in status {order.status}'}), 400

    order.status = 'in_progress'
    db.session.commit()
    return jsonify(order.to_dict()), 200

@orders_bp.route('/<int:order_id>/complete', methods=['PATCH'])
@jwt_required()
def complete_order(order_id):
    """Водитель завершает поездку"""
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if claims.get('role') != 'driver':
        return jsonify({'msg': 'Only drivers can complete orders'}), 403

    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({'msg': 'Order not found'}), 404
    if order.driver_id != user_id:
        return jsonify({'msg': 'You are not assigned to this order'}), 403
    if order.status != 'in_progress':
        return jsonify({'msg': f'Cannot complete order in status {order.status}'}), 400

    order.status = 'completed'
    # Освобождаем водителя, если у него нет других активных заказов
    driver = db.session.get(User, user_id)
    active_orders = Order.query.filter(
        Order.driver_id == user_id,
        Order.status.in_(['assigned', 'accepted', 'in_progress'])
    ).count()
    if active_orders == 0:
        driver.is_available = True

    db.session.commit()
    return jsonify(order.to_dict()), 200

@orders_bp.route('/<int:order_id>/cancel', methods=['PATCH'])
@jwt_required()
def cancel_order(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({'msg': 'Order not found'}), 404
    if order.status in ['completed', 'cancelled']:
        return jsonify({'msg': 'Cannot cancel'}), 400

    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') == 'admin' or order.customer_id == user_id:
        driver = order.driver
        if driver and order.status in ['assigned', 'accepted', 'in_progress']:
            active_orders = Order.query.filter(
                Order.driver_id == driver.id,
                Order.id != order.id,
                Order.status.in_(['assigned', 'accepted', 'in_progress'])
            ).count()
            if active_orders == 0:
                driver.is_available = True

        order.status = 'cancelled'
        db.session.commit()
        return jsonify(order.to_dict()), 200
    else:
        return jsonify({'msg': 'Not authorized'}), 403