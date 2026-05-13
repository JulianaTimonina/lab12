from flask import Blueprint, request, jsonify
from models import db, Tariff, Order
from decorators import admin_required
from flask_jwt_extended import jwt_required

tariffs_bp = Blueprint('tariffs', __name__, url_prefix='/tariffs')

@tariffs_bp.route('', methods=['GET'])
@jwt_required()
def list_tariffs():
    tariffs = Tariff.query.all()
    return jsonify([t.to_dict() for t in tariffs]), 200

@tariffs_bp.route('', methods=['POST'])
@admin_required
def create_tariff():
    data = request.get_json()
    if not data or not data.get('name') or data.get('price_per_km') is None:
        return jsonify({'msg': 'Missing fields'}), 400
    if Tariff.query.filter_by(name=data['name']).first():
        return jsonify({'msg': 'Tariff already exists'}), 409

    tariff = Tariff(
        name=data['name'],
        base_fee=data.get('base_fee', 0.0),
        price_per_km=data['price_per_km'],
        currency=data.get('currency', 'USD'),
        description=data.get('description', '')
    )
    db.session.add(tariff)
    db.session.commit()
    return jsonify(tariff.to_dict()), 201

@tariffs_bp.route('/<int:tariff_id>', methods=['PUT'])
@admin_required
def update_tariff(tariff_id):
    tariff = db.session.get(Tariff, tariff_id)
    if tariff is None:
        return jsonify({'msg': 'Tariff not found'}), 404
    data = request.get_json()
    if 'name' in data: tariff.name = data['name']
    if 'base_fee' in data: tariff.base_fee = data['base_fee']
    if 'price_per_km' in data: tariff.price_per_km = data['price_per_km']
    if 'currency' in data: tariff.currency = data['currency']
    if 'description' in data: tariff.description = data['description']
    db.session.commit()
    return jsonify(tariff.to_dict()), 200

@tariffs_bp.route('/<int:tariff_id>', methods=['DELETE'])
@admin_required
def delete_tariff(tariff_id):
    tariff = db.session.get(Tariff, tariff_id)
    if tariff is None:
        return jsonify({'msg': 'Tariff not found'}), 404

    # Проверяем, используется ли тариф в незавершённых заказах
    active_orders = Order.query.filter(
        Order.tariff_id == tariff_id,
        Order.status.in_(['pending', 'assigned', 'accepted', 'in_progress'])
    ).count()
    if active_orders > 0:
        return jsonify({'msg': 'Cannot delete tariff with active orders'}), 400

    db.session.delete(tariff)
    db.session.commit()
    return jsonify({'msg': 'Tariff deleted'}), 200