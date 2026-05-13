from flask import Blueprint, jsonify, request
from models import db, Order, User
from sqlalchemy import func
from datetime import datetime, timedelta
from decorators import admin_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/daily-summary', methods=['GET'])
@admin_required
def daily_summary():
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')
    try:
        if start_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
        else:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1)
        else:
            end_date = datetime.utcnow() + timedelta(days=1)
    except ValueError:
        return jsonify({'msg': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    results = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('count'),
        func.sum(Order.cost).label('revenue')
    ).filter(
        Order.created_at >= start_date,
        Order.created_at < end_date,
        Order.status == 'completed'
    ).group_by(func.date(Order.created_at)).order_by('date').all()

    data = [{'date': str(r.date), 'orders': r.count, 'revenue': float(r.revenue or 0)} for r in results]
    return jsonify(data), 200

@reports_bp.route('/driver-performance', methods=['GET'])
@admin_required
def driver_performance():
    results = db.session.query(
        User.id,
        User.name,
        func.count(Order.id).label('completed_orders'),
        func.sum(Order.cost).label('total_revenue')
    ).join(Order, Order.driver_id == User.id).filter(
        Order.status == 'completed',
        User.role == 'driver'
    ).group_by(User.id).all()

    data = [{
        'driver_id': r.id,
        'driver_name': r.name,
        'completed_orders': r.completed_orders,
        'total_revenue': float(r.total_revenue or 0)
    } for r in results]
    return jsonify(data), 200