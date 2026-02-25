import pytest
from app import db
from app.models import User, Category, Supplier, Product, WarehouseCell, StockBalance, Document, DocumentItem
from datetime import datetime, date

def test_user_model(app):
    """Тестирование модели User"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            role='manager'
        )
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('password123') is True
        assert user.check_password('wrong') is False
        assert user.is_manager() is True
        assert user.is_admin() is False

def test_category_model(app):
    """Тестирование модели Category"""
    with app.app_context():
        category = Category(
            name='Тестовая категория',
            description='Описание тестовой категории'
        )
        
        db.session.add(category)
        db.session.commit()
        
        assert category.id is not None
        assert category.name == 'Тестовая категория'
        assert str(category) == '<Category Тестовая категория>'

def test_supplier_model(app):
    """Тестирование модели Supplier"""
    with app.app_context():
        supplier = Supplier(
            name='ООО Тест',
            inn='1234567890',
            contact_person='Иванов Иван',
            phone='+7 (999) 123-45-67',
            email='test@test.ru',
            address='г. Москва, ул. Тестовая'
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        assert supplier.id is not None
        assert supplier.name == 'ООО Тест'
        assert supplier.inn == '1234567890'
        assert str(supplier) == '<Supplier ООО Тест>'

def test_product_model(app, test_categories, test_supplier):
    """Тестирование модели Product"""
    with app.app_context():
        # Получаем объекты по ID
        category = db.session.get(Category, test_categories[0])
        supplier = db.session.get(Supplier, test_supplier)
        
        product = Product(
            article='TEST123',
            name='Тестовый продукт',
            unit='шт',
            price=1500.00,
            category_id=category.id,
            supplier_id=supplier.id
        )
        
        db.session.add(product)
        db.session.commit()
        
        assert product.id is not None
        assert product.article == 'TEST123'
        assert product.name == 'Тестовый продукт'
        assert float(product.price) == 1500.00
        assert product.category.name == category.name

def test_warehouse_cell_model(app):
    """Тестирование модели WarehouseCell"""
    with app.app_context():
        cell = WarehouseCell(
            name='Z-99',
            description='Тестовая ячейка'
        )
        
        db.session.add(cell)
        db.session.commit()
        
        assert cell.id is not None
        assert cell.name == 'Z-99'
        assert str(cell) == '<Cell Z-99>'

def test_stock_balance_model(app, test_products, test_cells):
    """Тестирование модели StockBalance"""
    with app.app_context():
        balance = StockBalance(
            product_id=test_products[0],
            cell_id=test_cells[0],
            quantity=100
        )
        
        db.session.add(balance)
        db.session.commit()
        
        assert balance.id is not None
        assert float(balance.quantity) == 100
        # Проверяем связи
        product = db.session.get(Product, test_products[0])
        assert balance.product.article == product.article

def test_document_model(app, test_supplier, admin_user):
    """Тестирование модели Document"""
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='ПН-202503-0001',
            doc_date=date.today(),
            supplier_id=test_supplier,
            author_id=admin_user,
            status='draft'
        )
        
        db.session.add(doc)
        db.session.commit()
        
        assert doc.id is not None
        assert doc.doc_number == 'ПН-202503-0001'
        assert doc.is_draft() is True
        assert doc.is_posted() is False
        assert doc.total_amount() == 0

def test_document_item_model(app, test_products):
    """Тестирование модели DocumentItem"""
    with app.app_context():
        # Создаем документ
        doc = Document(
            doc_type='income',
            doc_number='ПН-202503-0002',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=10,
            price=1000.00
        )
        
        db.session.add(item)
        db.session.commit()
        
        assert item.id is not None
        assert float(item.quantity) == 10
        assert float(item.price) == 1000.00
        assert float(item.total()) == 10000.00