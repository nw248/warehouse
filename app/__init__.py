from flask import Flask, render_template  # ДОЛЖЕН БЫТЬ render_template!
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_jwt_extended import JWTManager
from config import Config
from datetime import datetime

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
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему'
    login_manager.login_message_category = 'warning'
    
    # Регистрация blueprint'ов
    from app.routes.auth import bp as auth_bp
    from app.routes.products import bp as products_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.reports import bp as reports_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}
    
    @app.route('/')
    def index():
        from app.models import Product, Supplier, Document, User, StockBalance
        from sqlalchemy import func
        
        stats = {
            'products_count': Product.query.count(),
            'suppliers_count': Supplier.query.count(),
            'documents_count': Document.query.count(),
            'users_count': User.query.count()
        }
        
        recent_documents = Document.query.order_by(Document.created_at.desc()).limit(5).all()
        
        low_stock = []
        products = Product.query.all()
        for product in products:
            total = db.session.query(func.sum(StockBalance.quantity)).filter_by(
                product_id=product.id
            ).scalar() or 0
            if total > 0 and total < 10:
                low_stock.append({
                    'id': product.id,
                    'name': product.name,
                    'article': product.article,
                    'quantity': float(total)
                })
        
        return render_template('index.html', 
                             stats=stats, 
                             recent_documents=recent_documents,
                             low_stock=low_stock[:5])
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))