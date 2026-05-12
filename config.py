import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///taxi.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT храним в cookies (httpOnly) – фронтенду не нужно управлять токенами
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_COOKIE_PATH = '/'
    JWT_REFRESH_COOKIE_PATH = '/token/refresh'
    JWT_COOKIE_CSRF_PROTECT = False      # для простоты отключено, на продакшене включить
    JWT_ACCESS_COOKIE_NAME = 'access_token'
    JWT_REFRESH_COOKIE_NAME = 'refresh_token'