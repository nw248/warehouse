from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    
    # Регистрация blueprint'ов
    from app.routes.auth import bp as auth_bp
    from app.routes.products import bp as products_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.reports import bp as reports_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    # Главная страница
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app