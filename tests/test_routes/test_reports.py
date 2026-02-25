import pytest
from app import db
from app.models import Product, Category, Supplier, Document, DocumentItem, StockBalance
from datetime import date, timedelta

def test_stock_report_page(client, auth, test_products, app):
    """Тест страницы отчета по остаткам"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
        balance = StockBalance(
            product_id=product.id,
            cell_id=1,
            quantity=100
        )
        db.session.add(balance)
        db.session.commit()
        
        response = client.get('/reports/stock')
        assert response.status_code == 200
        assert 'Отчет по остаткам'.encode('utf-8') in response.data

def test_stock_report_empty(client, auth):
    """Тест отчета по остаткам когда нет товаров"""
    auth.login()
    response = client.get('/reports/stock')
    assert response.status_code == 200
    assert 'Отчет по остаткам'.encode('utf-8') in response.data

def test_turnover_report_page(client, auth, test_products, app):
    """Тест страницы отчета по обороту"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
        
        # Создаем приходной документ
        doc = Document(
            doc_type='income',
            doc_number='ТЕСТ-001',
            doc_date=date.today(),
            status='posted'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=product.id,
            quantity=10,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
    
    # Тестируем разные периоды
    for period in ['week', 'month', 'quarter', 'year']:
        response = client.get(f'/reports/turnover?period={period}')
        assert response.status_code == 200
        assert 'Отчет по обороту'.encode('utf-8') in response.data

def test_turnover_report_with_category_filter(client, auth, test_categories, app):
    """Тест отчета по обороту с фильтром по категории"""
    auth.login()
    response = client.get(f'/reports/turnover?category_id={test_categories[0]}')
    assert response.status_code == 200

def test_suppliers_report_page(client, auth, test_supplier, app):
    """Тест страницы отчета по поставщикам"""
    auth.login()
    response = client.get('/reports/suppliers')
    assert response.status_code == 200
    assert 'Отчет по поставщикам'.encode('utf-8') in response.data

def test_product_movement_page(client, auth, test_products, app):
    """Тест страницы движения товара"""
    auth.login()
    
    with app.app_context():
        product_id = test_products[0]
        product = db.session.get(Product, product_id)
        
        # Создаем документ
        doc = Document(
            doc_type='income',
            doc_number='ТЕСТ-002',
            doc_date=date.today(),
            status='posted'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=product.id,
            quantity=10,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
        
        response = client.get(f'/reports/movement/{product.id}')
        assert response.status_code == 200
        assert 'Движение товара'.encode('utf-8') in response.data

def test_product_movement_with_date_filter(client, auth, test_products, app):
    """Тест движения товара с фильтром по датам"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
        
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        response = client.get(
            f'/reports/movement/{product.id}',
            query_string={
                'date_from': week_ago.isoformat(),
                'date_to': today.isoformat()
            }
        )
        assert response.status_code == 200

def test_export_stock_csv(client, auth, test_products, app):
    """Тест экспорта остатков в CSV"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
        balance = StockBalance(
            product_id=product.id,
            cell_id=1,
            quantity=100
        )
        db.session.add(balance)
        db.session.commit()
    
    response = client.get('/reports/export/stock')
    assert response.status_code == 200
    assert 'text/csv' in response.headers['Content-Type']
    assert '.csv' in response.headers['Content-Disposition']

def test_export_turnover_csv(client, auth, test_products, app):
    """Тест экспорта оборота в CSV"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
        doc = Document(
            doc_type='income',
            doc_number='ТЕСТ-003',
            doc_date=date.today(),
            status='posted'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=product.id,
            quantity=10,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
    
    response = client.get('/reports/export/turnover?period=month')
    assert response.status_code == 200
    assert 'text/csv' in response.headers['Content-Type']

def test_reports_access_without_login(client):
    """Тест доступа к отчетам без авторизации"""
    response = client.get('/reports/stock')
    assert response.status_code == 302
    
    response = client.get('/reports/turnover')
    assert response.status_code == 302