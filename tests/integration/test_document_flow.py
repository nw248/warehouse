import pytest
from app import db
from app.models import Document, StockBalance, Product

def test_full_document_flow(client, auth, test_products, app):
    """Тест полного цикла работы с документами"""
    # Логинимся
    login_response = auth.login()
    assert login_response.status_code == 200
    
    with app.app_context():
        product1 = db.session.get(Product, test_products[0])
        product2 = db.session.get(Product, test_products[1])
        
        # Создаем приходной документ
        response = client.post('/documents/create', data={
            'doc_type': 'income',
            'doc_date': '2025-03-25',
            'product_0': product1.id,
            'quantity_0': 10,
            'price_0': 1000,
            'product_1': product2.id,
            'quantity_1': 5,
            'price_1': 500
        }, follow_redirects=True)
        
        # Проверяем успешность создания
        assert response.status_code == 200
        
        # Находим созданный документ
        doc = Document.query.filter_by(doc_type='income').order_by(Document.id.desc()).first()
        assert doc is not None
        assert doc.status == 'draft'
        
        # Проводим документ
        response = client.post(f'/documents/{doc.id}/post', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверяем остатки
        balance1 = StockBalance.query.filter_by(product_id=product1.id).first()
        balance2 = StockBalance.query.filter_by(product_id=product2.id).first()
        
        assert balance1 is not None
        assert balance2 is not None
        assert float(balance1.quantity) == 10
        assert float(balance2.quantity) == 5

def test_expense_insufficient_flow(client, auth, test_products, app):
    """Тест попытки расхода при недостатке товара"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
        
        # Создаем расходной документ
        response = client.post('/documents/create', data={
            'doc_type': 'expense',
            'doc_date': '2025-03-25',
            'product_0': product.id,
            'quantity_0': 100,
            'price_0': 1000
        }, follow_redirects=True)
        
        # Проверяем создание
        assert response.status_code == 200
        
        # Находим документ
        doc = Document.query.filter_by(doc_type='expense').order_by(Document.id.desc()).first()
        assert doc is not None
        assert doc.status == 'draft'
        
        # Пытаемся провести - должно быть ошибка
        response = client.post(f'/documents/{doc.id}/post', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверяем, что статус остался черновиком
        db.session.refresh(doc)
        assert doc.status == 'draft'