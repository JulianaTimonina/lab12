from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config
from models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Инициализация расширений
    db.init_app(app)
    jwt = JWTManager(app)

    # ---------- Регистрация Blueprint'ов ----------
    # Пока что эти модули содержат только сам объект Blueprint
    from routes.auth import auth_bp
    from routes.orders import orders_bp
    from routes.drivers import drivers_bp
    from routes.tariffs import tariffs_bp
    from routes.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(drivers_bp, url_prefix='/drivers')
    app.register_blueprint(tariffs_bp, url_prefix='/tariffs')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # Простейший маршрут для проверки
    @app.route('/')
    def index():
        return 'Taxi app is running.'

    # Создание таблиц (при первом запуске)
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8080)