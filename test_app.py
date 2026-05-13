"""
Расширенные тесты для taxi_app.
Ожидаемое покрытие строк: >=95%.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app import create_app
from models import db, User, Tariff, Order
from geocoding.utils import get_coordinates, calculate_distance

# ------------------- Фикстуры -------------------
@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret',
        'SECRET_KEY': 'test-secret'
    })
    with app.app_context():
        db.create_all()
        seed_test_data_in_db()
    yield app
    with app.app_context():
        db.drop_all()

def seed_test_data_in_db():
    """Добавляет тестовых пользователей и тарифы поверх сидирования."""
    driver = User(email='driver@test.com', name='Driver', role='driver', phone='1', vehicle='Lada', is_available=True)
    driver.set_password('driver')
    driver2 = User(email='driver2@test.com', name='Driver2', role='driver', phone='2', vehicle='Volga', is_available=True)
    driver2.set_password('driver2')
    customer = User(email='customer@test.com', name='Customer', role='customer', phone='3')
    customer.set_password('customer')
    db.session.add_all([driver, driver2, customer])
    t1 = Tariff(name='Econom', base_fee=2.0, price_per_km=0.5)
    t2 = Tariff(name='Business', base_fee=5.0, price_per_km=1.5)
    db.session.add_all([t1, t2])
    db.session.commit()

@pytest.fixture
def client(app):
    return app.test_client()

def login(client, email, password):
    resp = client.post('/auth/login', json={'email': email, 'password': password})
    return json.loads(resp.data)['access_token']

# Мок для геокодирования, используемый в тестах заказов (autouse)
@pytest.fixture(autouse=True)
def mock_geocoding():
    with patch('geocoding.utils.get_coordinates', return_value=(55.7558, 37.6173)), \
         patch('geocoding.utils.calculate_distance', return_value=10.0):
        yield

# ------------------- Тесты страниц (app.py) -------------------
def test_index_page(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'login' in resp.data.lower()

def test_login_page(client):
    resp = client.get('/login')
    assert resp.status_code == 200

def test_register_page(client):
    resp = client.get('/register')
    assert resp.status_code == 200

def test_customer_page(client):
    resp = client.get('/customer')
    assert resp.status_code == 200

def test_driver_page(client):
    resp = client.get('/driver')
    assert resp.status_code == 200

def test_admin_dashboard_page(client):
    resp = client.get('/admin/dashboard')
    assert resp.status_code == 200

def test_admin_drivers_page(client):
    resp = client.get('/admin/drivers')
    assert resp.status_code == 200

def test_admin_tariffs_page(client):
    resp = client.get('/admin/tariffs')
    assert resp.status_code == 200

def test_admin_reports_page(client):
    resp = client.get('/admin/reports')
    assert resp.status_code == 200

# ------------------- Модели -------------------
def test_user_password_hashing(app):
    with app.app_context():
        user = User(email='a@b.c', name='Test')
        user.set_password('123')
        assert user.check_password('123')
        assert not user.check_password('wrong')

def test_user_to_dict(app):
    with app.app_context():
        user = User.query.filter_by(email='admin@admin.com').first()
        d = user.to_dict()
        assert set(d.keys()) == {'id', 'email', 'role', 'name', 'phone', 'vehicle', 'is_available'}

def test_tariff_to_dict(app):
    with app.app_context():
        tariff = Tariff.query.first()
        d = tariff.to_dict()
        assert 'id' in d and 'name' in d and 'base_fee' in d and 'price_per_km' in d

def test_order_to_dict(app):
    with app.app_context():
        customer = User.query.filter_by(role='customer').first()
        tariff = Tariff.query.first()
        order = Order(customer_id=customer.id, tariff_id=tariff.id, pickup_address='A', destination_address='B',
                      pickup_lat=0, pickup_lon=0, dest_lat=0, dest_lon=0, distance_km=10, cost=100, status='pending')
        db.session.add(order)
        db.session.commit()
        d = order.to_dict()
        assert d['customer_name'] == customer.name
        assert d['driver_name'] is None
        assert d['tariff_name'] == tariff.name

# ------------------- Auth -------------------
def test_register_missing_fields(client):
    resp = client.post('/auth/register', json={})
    assert resp.status_code == 400

def test_register_success(client):
    resp = client.post('/auth/register', json={
        'email': 'new@test.com', 'password': 'pass', 'name': 'New'
    })
    assert resp.status_code == 201

def test_register_duplicate_email(client):
    resp = client.post('/auth/register', json={
        'email': 'admin@admin.com', 'password': 'pass', 'name': 'Dup'
    })
    assert resp.status_code == 409

def test_login_invalid_credentials(client):
    resp = client.post('/auth/login', json={'email': 'admin@admin.com', 'password': 'wrong'})
    assert resp.status_code == 401

def test_login_missing_fields(client):
    resp = client.post('/auth/login', json={})
    assert resp.status_code == 400

def test_login_success(client):
    resp = client.post('/auth/login', json={'email': 'customer@test.com', 'password': 'customer'})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'access_token' in data and 'refresh_token' in data

def test_me_valid_token(client):
    token = login(client, 'customer@test.com', 'customer')
    resp = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['role'] == 'customer'

def test_me_invalid_token(client):
    resp = client.get('/auth/me', headers={'Authorization': 'Bearer badtoken'})
    assert resp.status_code == 422

def test_me_user_not_found(app, client):
    # Создаём токен, потом удаляем пользователя вручную в контексте
    token = login(client, 'customer@test.com', 'customer')
    with app.app_context():
        user = User.query.filter_by(email='customer@test.com').first()
        db.session.delete(user)
        db.session.commit()
    resp = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_refresh_token_valid(client):
    login_resp = client.post('/auth/login', json={'email': 'admin@admin.com', 'password': 'admin'})
    refresh_token = json.loads(login_resp.data)['refresh_token']
    resp = client.post('/auth/refresh', headers={'Authorization': f'Bearer {refresh_token}'})
    assert resp.status_code == 200

def test_refresh_no_token(client):
    resp = client.post('/auth/refresh')
    assert resp.status_code == 401  # или 422

# ------------------- Tariffs -------------------
def test_list_tariffs(client):
    token = login(client, 'customer@test.com', 'customer')
    resp = client.get('/tariffs', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert len(json.loads(resp.data)) == 5  # 3 seed + 2 test

def test_create_tariff_missing_name(client):
    token = login(client, 'admin@admin.com', 'admin')
    resp = client.post('/tariffs', json={'price_per_km': 1.0}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 400

def test_create_tariff_duplicate_name(client):
    token = login(client, 'admin@admin.com', 'admin')
    # Эконом уже существует
    resp = client.post('/tariffs', json={'name': 'Эконом', 'price_per_km': 1.0}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 409

def test_create_tariff_negative_price(client):
    token = login(client, 'admin@admin.com', 'admin')
    resp = client.post('/tariffs', json={'name': 'Neg', 'price_per_km': -0.5}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 400

def test_create_tariff_admin_required(client):
    token = login(client, 'customer@test.com', 'customer')
    resp = client.post('/tariffs', json={'name': 'Lux', 'price_per_km': 2.0}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 403

def test_update_tariff_negative_base_fee(client):
    token = login(client, 'admin@admin.com', 'admin')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token}'}).data)
    tid = tariffs[0]['id']
    resp = client.put(f'/tariffs/{tid}', json={'base_fee': -1}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 400

def test_update_tariff_not_found(client):
    token = login(client, 'admin@admin.com', 'admin')
    resp = client.put('/tariffs/999', json={'name': 'New'}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_delete_tariff_not_found(client):
    token = login(client, 'admin@admin.com', 'admin')
    resp = client.delete('/tariffs/999', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_delete_tariff_without_active_orders(client):
    token = login(client, 'admin@admin.com', 'admin')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token}'}).data)
    # Выбираем тариф, у которого нет заказов
    tid = tariffs[-1]['id']  # последний добавленный
    resp = client.delete(f'/tariffs/{tid}', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200

def test_delete_tariff_with_active_orders(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    token_admin = login(client, 'admin@admin.com', 'admin')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_admin}'}).data)
    tid = tariffs[0]['id']
    client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    resp = client.delete(f'/tariffs/{tid}', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 400

# ------------------- Orders -------------------
def test_create_order_missing_fields(client):
    token = login(client, 'customer@test.com', 'customer')
    resp = client.post('/orders', json={}, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 400

def test_create_order_invalid_tariff(client):
    token = login(client, 'customer@test.com', 'customer')
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': 999
    }, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_create_order_as_customer(client):
    token = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'Moscow', 'destination_address': 'Piter', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 201
    assert json.loads(resp.data)['status'] == 'pending'

def test_create_order_as_driver_forbidden(client):
    token = login(client, 'driver@test.com', 'driver')
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': 1
    }, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 403

def test_get_orders_roles(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    for i in range(2):
        client.post('/orders', json={
            'pickup_address': f'Addr{i}', 'destination_address': f'Dest{i}', 'tariff_id': tid
        }, headers={'Authorization': f'Bearer {token_cust}'})
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.get('/orders', headers={'Authorization': f'Bearer {token_admin}'})
    assert len(json.loads(resp.data)) == 2
    resp = client.get('/orders', headers={'Authorization': f'Bearer {token_cust}'})
    assert len(json.loads(resp.data)) == 2
    token_driver = login(client, 'driver@test.com', 'driver')
    resp = client.get('/orders', headers={'Authorization': f'Bearer {token_driver}'})
    assert len(json.loads(resp.data)) == 2

def test_take_order_driver(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'X', 'destination_address': 'Y', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_driver = login(client, 'driver@test.com', 'driver')
    resp = client.patch(f'/orders/{order_id}/take', headers={'Authorization': f'Bearer {token_driver}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['status'] == 'assigned'
    # Другой водитель не может взять
    token_driver2 = login(client, 'driver2@test.com', 'driver2')
    resp = client.patch(f'/orders/{order_id}/take', headers={'Authorization': f'Bearer {token_driver2}'})
    assert resp.status_code == 400

def test_take_order_not_driver(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'X', 'destination_address': 'Y', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    resp = client.patch(f'/orders/{order_id}/take', headers={'Authorization': f'Bearer {token_cust}'})
    assert resp.status_code == 403

def test_driver_cannot_take_second_order(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    ids = []
    for addr in ['A', 'B']:
        r = client.post('/orders', json={
            'pickup_address': addr, 'destination_address': 'Z', 'tariff_id': tid
        }, headers={'Authorization': f'Bearer {token_cust}'})
        ids.append(json.loads(r.data)['id'])
    token_driver = login(client, 'driver@test.com', 'driver')
    client.patch(f'/orders/{ids[0]}/take', headers={'Authorization': f'Bearer {token_driver}'})
    resp = client.patch(f'/orders/{ids[1]}/take', headers={'Authorization': f'Bearer {token_driver}'})
    assert resp.status_code == 400
    assert 'active order' in json.loads(resp.data)['msg']

def test_order_lifecycle(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'Start', 'destination_address': 'End', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_driver = login(client, 'driver@test.com', 'driver')
    client.patch(f'/orders/{order_id}/take', headers={'Authorization': f'Bearer {token_driver}'})
    # accept
    resp = client.patch(f'/orders/{order_id}/accept', headers={'Authorization': f'Bearer {token_driver}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['status'] == 'accepted'
    # start
    resp = client.patch(f'/orders/{order_id}/start', headers={'Authorization': f'Bearer {token_driver}'})
    assert json.loads(resp.data)['status'] == 'in_progress'
    # complete
    resp = client.patch(f'/orders/{order_id}/complete', headers={'Authorization': f'Bearer {token_driver}'})
    assert json.loads(resp.data)['status'] == 'completed'
    # driver is available again
    token_admin = login(client, 'admin@admin.com', 'admin')
    drivers = json.loads(client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'}).data)
    d = next(d for d in drivers if d['email'] == 'driver@test.com')
    assert d['is_available'] == True

def test_assign_driver_admin(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_admin = login(client, 'admin@admin.com', 'admin')
    drivers = json.loads(client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'}).data)
    driver_id = drivers[0]['id']
    resp = client.patch(f'/orders/{order_id}/assign', json={'driver_id': driver_id},
                        headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['status'] == 'assigned'

def test_assign_unavailable_driver(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_admin = login(client, 'admin@admin.com', 'admin')
    drivers = json.loads(client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'}).data)
    driver = drivers[0]
    client.put(f'/drivers/{driver["id"]}', json={'is_available': False},
               headers={'Authorization': f'Bearer {token_admin}'})
    resp = client.patch(f'/orders/{order_id}/assign', json={'driver_id': driver['id']},
                        headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 400

def test_assign_order_not_pending(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_admin = login(client, 'admin@admin.com', 'admin')
    drivers = json.loads(client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'}).data)
    driver_id = drivers[0]['id']
    # сначала назначаем
    client.patch(f'/orders/{order_id}/assign', json={'driver_id': driver_id},
                 headers={'Authorization': f'Bearer {token_admin}'})
    # пытаемся назначить повторно
    resp = client.patch(f'/orders/{order_id}/assign', json={'driver_id': drivers[1]['id']},
                        headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 400

def test_cancel_order_by_admin(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.patch(f'/orders/{order_id}/cancel', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['status'] == 'cancelled'

def test_cancel_order_customer(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    resp = client.patch(f'/orders/{order_id}/cancel', headers={'Authorization': f'Bearer {token_cust}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['status'] == 'cancelled'

def test_cancel_order_not_owner_or_admin(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_driver = login(client, 'driver@test.com', 'driver')
    resp = client.patch(f'/orders/{order_id}/cancel', headers={'Authorization': f'Bearer {token_driver}'})
    assert resp.status_code == 403

def test_cancel_completed_order(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_driver = login(client, 'driver@test.com', 'driver')
    client.patch(f'/orders/{order_id}/take', headers={'Authorization': f'Bearer {token_driver}'})
    client.patch(f'/orders/{order_id}/accept', headers={'Authorization': f'Bearer {token_driver}'})
    client.patch(f'/orders/{order_id}/start', headers={'Authorization': f'Bearer {token_driver}'})
    client.patch(f'/orders/{order_id}/complete', headers={'Authorization': f'Bearer {token_driver}'})
    resp = client.patch(f'/orders/{order_id}/cancel', headers={'Authorization': f'Bearer {token_cust}'})
    assert resp.status_code == 400

# ------------------- Drivers -------------------
def test_get_drivers_admin(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200
    assert len(json.loads(resp.data)) >= 2

def test_create_driver_missing_fields(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.post('/drivers', json={}, headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 400

def test_create_driver_duplicate_email(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.post('/drivers', json={
        'email': 'driver@test.com', 'password': 'pass', 'name': 'Dup'
    }, headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 409

def test_create_driver_success(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.post('/drivers', json={
        'email': 'newdriver@test.com', 'password': 'pass', 'name': 'NewDriver', 'phone': '555'
    }, headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 201

def test_update_driver_not_found(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.put('/drivers/999', json={'name': 'Ghost'}, headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 404

def test_delete_driver_not_found(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.delete('/drivers/999', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 404

def test_delete_driver_with_active_order(client):
    token_cust = login(client, 'customer@test.com', 'customer')
    tariffs = json.loads(client.get('/tariffs', headers={'Authorization': f'Bearer {token_cust}'}).data)
    tid = tariffs[0]['id']
    resp = client.post('/orders', json={
        'pickup_address': 'A', 'destination_address': 'B', 'tariff_id': tid
    }, headers={'Authorization': f'Bearer {token_cust}'})
    order_id = json.loads(resp.data)['id']
    token_driver = login(client, 'driver@test.com', 'driver')
    client.patch(f'/orders/{order_id}/take', headers={'Authorization': f'Bearer {token_driver}'})
    token_admin = login(client, 'admin@admin.com', 'admin')
    drivers = json.loads(client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'}).data)
    driver_id = next(d['id'] for d in drivers if d['email'] == 'driver@test.com')
    resp = client.delete(f'/drivers/{driver_id}', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 400

def test_delete_driver_without_active_orders(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    drivers = json.loads(client.get('/drivers', headers={'Authorization': f'Bearer {token_admin}'}).data)
    # выбираем свободного водителя (driver2)
    driver_id = next(d['id'] for d in drivers if d['email'] == 'driver2@test.com')
    resp = client.delete(f'/drivers/{driver_id}', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200

# ------------------- Reports -------------------
def test_daily_summary_default(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.get('/reports/daily-summary', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200
    assert isinstance(json.loads(resp.data), list)

def test_daily_summary_with_dates(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.get('/reports/daily-summary?start_date=2024-01-01&end_date=2024-01-31',
                      headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200

def test_daily_summary_invalid_date(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.get('/reports/daily-summary?start_date=01-01-2024',
                      headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 400

def test_driver_performance(client):
    token_admin = login(client, 'admin@admin.com', 'admin')
    resp = client.get('/reports/driver-performance', headers={'Authorization': f'Bearer {token_admin}'})
    assert resp.status_code == 200
    assert isinstance(json.loads(resp.data), list)

# ------------------- Geocoding utils -------------------
def test_get_coordinates_success():
    mock_geocode = MagicMock()
    mock_geocode.latitude = 55.7558
    mock_geocode.longitude = 37.6173
    with patch('geocoding.utils.geolocator.geocode', return_value=mock_geocode):
        lat, lon = get_coordinates('Moscow')
        assert lat == 55.7558
        assert lon == 37.6173

def test_get_coordinates_not_found():
    with patch('geocoding.utils.geolocator.geocode', return_value=None):
        with pytest.raises(ValueError, match='Address not found'):
            get_coordinates('Nowhere')

def test_calculate_distance():
    dist = calculate_distance(55.7558, 37.6173, 59.9343, 30.3351)  # Moscow to SPb
    assert dist > 600  # примерно 635 км