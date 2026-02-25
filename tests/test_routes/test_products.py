import pytest
from app import db
from app.models import Product, Category, Supplier, WarehouseCell, StockBalance
from datetime import date

def test_product_list_page(client, auth):
    """Тест страницы списка товаров"""
    auth.login()
    response = client.get('/products/')
    assert response.status_code == 200
    assert 'Товары'.encode('utf-8') in response.data

def test_product_create_page(client, auth):
    """Тест страницы создания товара"""
    auth.login()
    response = client.get('/products/create')
    assert response.status_code == 200
    assert 'Новый товар'.encode('utf-8') in response.data

def test_product_create_post(client, auth, test_categories, test_supplier):
    """Тест создания товара через POST"""
    auth.login()
    
    response = client.post('/products/create', data={
        'article': 'NEW001',
        'name': 'Новый тестовый товар',
        'unit': 'шт',
        'price': 999.99,
        'category_id': test_categories[0],
        'supplier_id': test_supplier
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'успешно'.encode('utf-8') in response.data

def test_product_edit_page(client, auth, test_products, app):
    """Тест страницы редактирования товара"""
    auth.login()
    
    with app.app_context():
        product_id = test_products[0]
        response = client.get(f'/products/{product_id}/edit')
        assert response.status_code == 200
        assert 'Редактирование'.encode('utf-8') in response.data

def test_product_edit_post(client, auth, test_products, app):
    """Тест обновления товара"""
    auth.login()
    
    with app.app_context():
        product_id = test_products[0]
        product = db.session.get(Product, product_id)
        
    response = client.post(f'/products/{product_id}/edit', data={
        'article': product.article,
        'name': 'Обновленное название',
        'unit': product.unit,
        'price': 1500.00,
        'category_id': product.category_id,
        'supplier_id': product.supplier_id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'обновлен'.encode('utf-8') in response.data

def test_product_delete_without_relations(client, auth, app):
    """Тест удаления товара без связей"""
    auth.login()
    
    with app.app_context():
        # Создаем товар без связей
        product = Product(
            article='DELETE001',
            name='Товар для удаления',
            unit='шт',
            price=100
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    
    response = client.post(f'/products/{product_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'удален'.encode('utf-8') in response.data

def test_product_delete_with_balances(client, auth, test_products, app):
    """Тест удаления товара с остатками (должно блокироваться)"""
    auth.login()
    
    with app.app_context():
        product_id = test_products[0]
        product = db.session.get(Product, product_id)
        # Создаем остаток
        balance = StockBalance(
            product_id=product_id,
            cell_id=1,
            quantity=10
        )
        db.session.add(balance)
        db.session.commit()
    
    response = client.post(f'/products/{product_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'Нельзя удалить'.encode('utf-8') in response.data

def test_category_list_page(client, auth):
    """Тест страницы категорий"""
    auth.login()
    response = client.get('/products/categories')
    assert response.status_code == 200
    assert 'Категории'.encode('utf-8') in response.data

def test_category_create_post(client, auth):
    """Тест создания категории"""
    auth.login()
    
    response = client.post('/products/categories/create', data={
        'name': 'Новая категория',
        'description': 'Описание новой категории'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'создана'.encode('utf-8') in response.data

def test_category_edit_post(client, auth, test_categories, app):
    """Тест редактирования категории"""
    auth.login()
    
    with app.app_context():
        category_id = test_categories[0]
    
    response = client.post(f'/products/categories/{category_id}/edit', data={
        'name': 'Обновленная категория',
        'description': 'Новое описание'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'обновлена'.encode('utf-8') in response.data

def test_category_delete_empty(client, auth, app):
    """Тест удаления пустой категории"""
    auth.login()
    
    with app.app_context():
        category = Category(name='Временная категория')
        db.session.add(category)
        db.session.commit()
        category_id = category.id
    
    response = client.post(f'/products/categories/{category_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'удалена'.encode('utf-8') in response.data

def test_category_delete_with_products(client, auth, test_categories, test_products, test_supplier, app):
    """Тест удаления категории с товарами (должно блокироваться)"""
    auth.login()
    
    category_id = None
    with app.app_context():
        # Берем первую категорию
        category_id = test_categories[0]
        category = db.session.get(Category, category_id)
        
        # Проверяем, есть ли товары в категории
        if category.products.count() == 0:
            # Создаем товар в этой категории
            product = Product(
                article='CATEGORY-TEST',
                name='Товар для теста категории',
                unit='шт',
                price=100,
                category_id=category_id,
                supplier_id=test_supplier
            )
            db.session.add(product)
            db.session.commit()
    
    # Пытаемся удалить категорию
    response = client.post(f'/products/categories/{category_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Проверяем, что категория не удалилась
        category = db.session.get(Category, category_id)
        assert category is not None

def test_supplier_list_page(client, auth):
    """Тест страницы поставщиков"""
    auth.login()
    response = client.get('/products/suppliers')
    assert response.status_code == 200
    assert 'Поставщики'.encode('utf-8') in response.data

def test_supplier_create_post(client, auth):
    """Тест создания поставщика"""
    auth.login()
    
    response = client.post('/products/suppliers/create', data={
        'name': 'Новый поставщик',
        'inn': '1234567890',
        'contact_person': 'Иван Иванов',
        'phone': '+7 (999) 123-45-67',
        'email': 'new@supplier.ru'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'создан'.encode('utf-8') in response.data

def test_supplier_edit_post(client, auth, test_supplier, app):
    """Тест редактирования поставщика"""
    auth.login()
    
    with app.app_context():
        response = client.post(f'/products/suppliers/{test_supplier}/edit', data={
            'name': 'Обновленный поставщик',
            'inn': '0987654321',
            'contact_person': 'Петр Петров',
            'phone': '+7 (999) 765-43-21',
            'email': 'updated@supplier.ru'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'обновлен'.encode('utf-8') in response.data

def test_cell_list_page(client, auth):
    """Тест страницы ячеек"""
    auth.login()
    response = client.get('/products/cells')
    assert response.status_code == 200
    assert 'Складские ячейки'.encode('utf-8') in response.data

def test_cell_create_post(client, auth):
    """Тест создания ячейки"""
    auth.login()
    
    response = client.post('/products/cells/create', data={
        'name': 'Z-99',
        'description': 'Новая тестовая ячейка'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'создана'.encode('utf-8') in response.data

def test_cell_delete_empty(client, auth, app):
    """Тест удаления пустой ячейки"""
    auth.login()
    
    with app.app_context():
        cell = WarehouseCell(name='TEMP-01')
        db.session.add(cell)
        db.session.commit()
        cell_id = cell.id
    
    response = client.post(f'/products/cells/{cell_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'удалена'.encode('utf-8') in response.data

def test_stock_page(client, auth):
    """Тест страницы остатков"""
    auth.login()
    response = client.get('/products/stock')
    assert response.status_code == 200
    assert 'Остатки'.encode('utf-8') in response.data

def test_stock_balance_filter(client, auth, test_products, app):
    """Тест фильтрации остатков"""
    auth.login()
    
    with app.app_context():
        product_id = test_products[0]
    
    response = client.get(f'/products/stock?product_id={product_id}')
    assert response.status_code == 200
    assert 'Остатки'.encode('utf-8') in response.data