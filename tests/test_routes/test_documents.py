import pytest
from app import db
from app.models import Document, DocumentItem, Product, Supplier, StockBalance
from datetime import date, datetime

def test_document_list_page(client, auth):
    """Тест страницы списка документов"""
    auth.login()
    response = client.get('/documents/')
    assert response.status_code == 200
    assert 'Документы'.encode('utf-8') in response.data

def test_document_list_page_with_filters(client, auth, app):
    """Тест страницы списка документов с фильтрами"""
    auth.login()
    
    with app.app_context():
        # Создаем тестовые документы
        doc1 = Document(
            doc_type='income',
            doc_number='INC-FILTER-001',
            doc_date=date(2025, 1, 15),
            status='posted'
        )
        doc2 = Document(
            doc_type='expense',
            doc_number='EXP-FILTER-001',
            doc_date=date(2025, 2, 20),
            status='draft'
        )
        db.session.add_all([doc1, doc2])
        db.session.commit()
    
    # Фильтр по типу
    response = client.get('/documents/?type=income')
    assert response.status_code == 200
    assert 'INC-FILTER-001'.encode('utf-8') in response.data
    
    # Фильтр по статусу
    response = client.get('/documents/?status=draft')
    assert response.status_code == 200
    assert 'EXP-FILTER-001'.encode('utf-8') in response.data
    
    # Фильтр по датам
    response = client.get('/documents/?date_from=2025-01-01&date_to=2025-01-31')
    assert response.status_code == 200
    assert 'INC-FILTER-001'.encode('utf-8') in response.data
    assert 'EXP-FILTER-001'.encode('utf-8') not in response.data

def test_document_create_page(client, auth):
    """Тест страницы создания документа"""
    auth.login()
    response = client.get('/documents/create')
    assert response.status_code == 200
    assert 'Новый документ'.encode('utf-8') in response.data

def test_document_create_post_income(client, auth, test_products, test_supplier, app):
    """Тест создания приходного документа через POST"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
    
    response = client.post('/documents/create', data={
        'doc_type': 'income',
        'doc_date': date.today().isoformat(),
        'supplier_id': test_supplier,
        'comment': 'Тестовый приход',
        'product_0': product.id,
        'quantity_0': 10,
        'price_0': 1000,
        'product_1': test_products[1],
        'quantity_1': 5,
        'price_1': 500
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'успешно'.encode('utf-8') in response.data
    
    with app.app_context():
        doc = Document.query.filter_by(doc_type='income').order_by(Document.id.desc()).first()
        assert doc is not None
        assert doc.doc_type == 'income'
        assert doc.status == 'draft'
        assert doc.items.count() == 2

def test_document_create_post_expense(client, auth, test_products, test_supplier, app):
    """Тест создания расходного документа через POST"""
    auth.login()
    
    with app.app_context():
        product = db.session.get(Product, test_products[0])
    
    response = client.post('/documents/create', data={
        'doc_type': 'expense',
        'doc_date': date.today().isoformat(),
        'supplier_id': test_supplier,
        'comment': 'Тестовый расход',
        'product_0': product.id,
        'quantity_0': 3,
        'price_0': 1000
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'успешно'.encode('utf-8') in response.data
    
    with app.app_context():
        doc = Document.query.filter_by(doc_type='expense').order_by(Document.id.desc()).first()
        assert doc is not None
        assert doc.doc_type == 'expense'
        assert doc.status == 'draft'

def test_document_create_no_items(client, auth, test_supplier):
    """Тест создания документа без товаров (должна быть ошибка)"""
    auth.login()
    
    response = client.post('/documents/create', data={
        'doc_type': 'income',
        'doc_date': date.today().isoformat(),
        'supplier_id': test_supplier,
        'comment': 'Документ без товаров'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'Добавьте хотя бы один товар'.encode('utf-8') in response.data

def test_document_view_page(client, auth, app):
    """Тест страницы просмотра документа"""
    auth.login()
    
    with app.app_context():
        # Создаем документ для просмотра
        doc = Document(
            doc_type='income',
            doc_number='VIEW-TEST-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=1,
            quantity=10,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
        doc_id = doc.id
    
    response = client.get(f'/documents/{doc_id}')
    assert response.status_code == 200
    assert 'VIEW-TEST-001'.encode('utf-8') in response.data

def test_document_edit_page(client, auth, app):
    """Тест страницы редактирования документа"""
    auth.login()
    
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='EDIT-TEST-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    response = client.get(f'/documents/{doc_id}/edit')
    assert response.status_code == 200
    assert 'Редактирование'.encode('utf-8') in response.data

def test_document_edit_post(client, auth, test_products, app):
    """Тест редактирования документа через POST"""
    auth.login()
    
    with app.app_context():
        # Создаем документ для редактирования
        doc = Document(
            doc_type='income',
            doc_number='EDIT-POST-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
        product = db.session.get(Product, test_products[0])
    
    response = client.post(f'/documents/{doc_id}/edit', data={
        'doc_type': 'income',
        'doc_date': date.today().isoformat(),
        'comment': 'Обновленный комментарий',
        'product_0': product.id,
        'quantity_0': 15,
        'price_0': 1200
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'обновлен'.encode('utf-8') in response.data
    
    with app.app_context():
        updated_doc = db.session.get(Document, doc_id)
        assert updated_doc.comment == 'Обновленный комментарий'
        assert updated_doc.items.count() == 1
        item = updated_doc.items.first()
        assert float(item.quantity) == 15
        assert float(item.price) == 1200

def test_document_edit_posted_document(client, auth, app):
    """Тест редактирования проведенного документа (должно быть ошибкой)"""
    auth.login()
    
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='EDIT-POSTED-001',
            doc_date=date.today(),
            status='posted'  # Уже проведен
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    response = client.get(f'/documents/{doc_id}/edit')
    assert response.status_code == 302  # Должно перенаправить

def test_document_post_success(client, auth, test_products, app):
    """Тест успешного проведения документа"""
    auth.login()
    
    with app.app_context():
        # Создаем документ
        doc = Document(
            doc_type='income',
            doc_number='POST-TEST-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=10,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
        doc_id = doc.id
    
    response = client.post(f'/documents/{doc_id}/post', follow_redirects=True)
    assert response.status_code == 200
    assert 'успешно'.encode('utf-8') in response.data
    
    with app.app_context():
        posted_doc = db.session.get(Document, doc_id)
        assert posted_doc.status == 'posted'

def test_document_post_already_posted(client, auth, app):
    """Тест повторного проведения документа"""
    auth.login()
    
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='POST-AGAIN-001',
            doc_date=date.today(),
            status='posted'  # Уже проведен
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    response = client.post(f'/documents/{doc_id}/post', follow_redirects=True)
    assert response.status_code == 200
    assert 'уже был проведен'.encode('utf-8') in response.data

def test_document_cancel_success(client, auth, test_products, app):
    """Тест успешной отмены документа"""
    auth.login()
    
    with app.app_context():
        # Создаем остаток товара
        balance = StockBalance(
            product_id=test_products[0],
            cell_id=1,
            quantity=20
        )
        db.session.add(balance)
        db.session.commit()
        
        # Создаем и проводим документ
        doc = Document(
            doc_type='income',
            doc_number='CANCEL-TEST-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=10,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
        
        # Проводим документ
        from app.services.stock_service import StockService
        StockService.process_income_document(doc)
        
        doc_id = doc.id
    
    # Отменяем документ
    response = client.post(f'/documents/{doc_id}/cancel', follow_redirects=True)
    assert response.status_code == 200
    assert 'успешно'.encode('utf-8') in response.data or 'отменён'.encode('utf-8') in response.data
    
    with app.app_context():
        cancelled_doc = db.session.get(Document, doc_id)
        assert cancelled_doc.status == 'cancelled'

def test_document_cancel_draft(client, auth, app):
    """Тест отмены черновика (должно быть ошибкой)"""
    auth.login()
    
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='CANCEL-DRAFT-001',
            doc_date=date.today(),
            status='draft'  # Черновик
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    response = client.post(f'/documents/{doc_id}/cancel', follow_redirects=True)
    assert response.status_code == 200
    assert 'только проведенный'.encode('utf-8') in response.data

def test_document_delete_draft(client, auth, app):
    """Тест удаления черновика"""
    auth.login()
    
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='DELETE-DRAFT-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    response = client.post(f'/documents/{doc_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'удален'.encode('utf-8') in response.data
    
    with app.app_context():
        deleted_doc = db.session.get(Document, doc_id)
        assert deleted_doc is None

def test_document_delete_posted(client, auth, app):
    """Тест удаления проведенного документа (должно быть ошибкой)"""
    auth.login()
    
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='DELETE-POSTED-001',
            doc_date=date.today(),
            status='posted'  # Проведен
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    response = client.post(f'/documents/{doc_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    # Проверяем, что документ не удалился
    with app.app_context():
        still_exists = db.session.get(Document, doc_id)
        assert still_exists is not None

def test_document_access_without_login(client, app):
    """Тест доступа к документам без авторизации"""
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='NO-LOGIN-001',
            doc_date=date.today(),
            status='draft'
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id
    
    # Все запросы должны перенаправлять на логин
    assert client.get('/documents/').status_code == 302
    assert client.get('/documents/create').status_code == 302
    assert client.get(f'/documents/{doc_id}').status_code == 302
    assert client.get(f'/documents/{doc_id}/edit').status_code == 302

def test_document_create_non_manager(client, auth, app):
    """Тест создания документа пользователем без прав"""
    # Создаем пользователя с ролью storekeeper
    with app.app_context():
        from app.models import User
        user = User(
            username='storekeeper',
            email='storekeeper@test.com',
            full_name='Store Keeper',
            role='storekeeper'
        )
        user.set_password('store123')
        db.session.add(user)
        db.session.commit()
    
    # Логинимся как кладовщик
    auth.login('storekeeper', 'store123')
    
    response = client.get('/documents/create')
    assert response.status_code == 302  # Должно перенаправить

def test_document_create_with_invalid_data(client, auth):
    """Тест создания документа с некорректными данными"""
    auth.login()
    
    response = client.post('/documents/create', data={
        'doc_type': 'invalid_type',  # Неверный тип
        'doc_date': 'not-a-date',
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Должна быть ошибка валидации