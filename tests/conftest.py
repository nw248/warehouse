import pytest
from app import create_app, db
from app.models import User, Category, Supplier, Product, WarehouseCell, StockBalance, Document, DocumentItem
from datetime import datetime, date

@pytest.fixture
def app():
    """Создание тестового приложения"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost.localdomain'
    
    with app.app_context():
        db.create_all()
        
        # СОЗДАЕМ ТЕСТОВОГО ПОЛЬЗОВАТЕЛЯ admin
        admin = User(
            username='admin',
            email='admin@test.com',
            full_name='Test Admin',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # СОЗДАЕМ ТЕСТОВОГО МЕНЕДЖЕРА
        manager = User(
            username='manager',
            email='manager@test.com',
            full_name='Test Manager',
            role='manager'
        )
        manager.set_password('manager123')
        db.session.add(manager)
        
        db.session.commit()
        
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Тестовый клиент"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Тестовый runner для команд"""
    return app.test_cli_runner()

@pytest.fixture
def auth(client):
    """Вспомогательный класс для аутентификации"""
    class AuthActions:
        def __init__(self, client):
            self._client = client
        
        def login(self, username='admin', password='admin123'):
            return self._client.post('/auth/login', data={
                'username': username,
                'password': password
            }, follow_redirects=True)
        
        def logout(self):
            return self._client.get('/auth/logout', follow_redirects=True)
    
    return AuthActions(client)

@pytest.fixture
def admin_user(app):
    """ID тестового администратора"""
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        return user.id

@pytest.fixture
def test_categories(app):
    """Создание тестовых категорий"""
    with app.app_context():
        categories = []
        for name in ['Электроинструмент', 'Ручной инструмент', 'Строительные материалы']:
            cat = Category(name=name)
            db.session.add(cat)
            categories.append(cat)
        db.session.commit()
        return [cat.id for cat in categories]

@pytest.fixture
def test_supplier(app):
    """Создание тестового поставщика"""
    with app.app_context():
        supplier = Supplier(
            name='Тестовый поставщик',
            inn='1234567890',
            contact_person='Тест Тестов',
            phone='+7 (999) 123-45-67',
            email='test@supplier.ru'
        )
        db.session.add(supplier)
        db.session.commit()
        return supplier.id

@pytest.fixture
def test_products(app, test_categories, test_supplier):
    """Создание тестовых товаров"""
    with app.app_context():
        products = []
        
        prod1 = Product(
            article='TEST001',
            name='Тестовый товар 1',
            unit='шт',
            price=1000.00,
            category_id=test_categories[0],
            supplier_id=test_supplier
        )
        prod2 = Product(
            article='TEST002',
            name='Тестовый товар 2',
            unit='кг',
            price=500.00,
            category_id=test_categories[1],
            supplier_id=test_supplier
        )
        
        db.session.add_all([prod1, prod2])
        db.session.commit()
        return [prod1.id, prod2.id]

@pytest.fixture
def test_cells(app):
    """Создание тестовых ячеек"""
    with app.app_context():
        cells = []
        for name in ['A-01', 'A-02', 'B-01']:
            cell = WarehouseCell(name=name)
            db.session.add(cell)
            cells.append(cell)
        db.session.commit()
        return [cell.id for cell in cells]