from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from config import Config
from models import db, User, Tariff

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    JWTManager(app)

    with app.app_context():
        db.create_all()
        seed_data(app)

    from auth.routes import auth_bp
    from orders.routes import orders_bp
    from drivers.routes import drivers_bp
    from tariffs.routes import tariffs_bp
    from reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(tariffs_bp)
    app.register_blueprint(reports_bp)

    # Публичные страницы (без JWT)
    @app.route('/')
    def index():
        return render_template('login.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        return render_template('register.html')

    # Страницы ролей — отдаём без проверки, клиент сам следит за токеном
    @app.route('/customer')
    def customer_page():
        return render_template('customer/dashboard.html')

    @app.route('/driver')
    def driver_page():
        return render_template('driver/dashboard.html')

    # Админские страницы (защищены только на уровне клиента)
    @app.route('/admin')
    @app.route('/admin/dashboard')
    def admin_dashboard():
        return render_template('admin/dashboard.html')

    @app.route('/admin/drivers')
    def admin_drivers():
        return render_template('admin/drivers.html')

    @app.route('/admin/tariffs')
    def admin_tariffs():
        return render_template('admin/tariffs.html')

    @app.route('/admin/reports')
    def admin_reports():
        return render_template('admin/reports.html')

    return app

def seed_data(app):
    with app.app_context():
        if not User.query.filter_by(role='admin').first():
            admin = User(
                email='admin@admin.com',
                name='Admin',
                role='admin',
                phone='0000000000',
                is_available=False
            )
            admin.set_password('admin')
            db.session.add(admin)

        if not Tariff.query.first():
            t1 = Tariff(name='Эконом', base_fee=2.0, price_per_km=0.5, description='Бюджетные поездки')
            t2 = Tariff(name='Комфорт', base_fee=4.0, price_per_km=0.8, description='Повышенный комфорт')
            t3 = Tariff(name='Бизнес', base_fee=6.0, price_per_km=1.2, description='Представительский класс')
            db.session.add_all([t1, t2, t3])

        db.session.commit()

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8080)