import pytest
from app import db
from app.models import Product, StockBalance, Document, DocumentItem, User, Category, Supplier, WarehouseCell
from app.services.stock_service import StockService
from datetime import date, datetime

def test_process_income_document_success(app, test_products, admin_user):
    """Тест успешного проведения приходного документа"""
    with app.app_context():
        # Создаем приходной документ
        doc = Document(
            doc_type='income',
            doc_number='INC-TEST-001',
            doc_date=date.today(),
            author_id=admin_user,
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        # Добавляем строки
        item1 = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=10,
            price=1000
        )
        item2 = DocumentItem(
            document_id=doc.id,
            product_id=test_products[1],
            quantity=5,
            price=500
        )
        db.session.add_all([item1, item2])
        db.session.commit()
        
        # Проводим документ
        success, message = StockService.process_income_document(doc)
        
        assert success is True
        assert doc.status == 'posted'
        assert doc.posted_at is not None
        
        # Проверяем остатки
        balance1 = StockBalance.query.filter_by(product_id=test_products[0]).first()
        balance2 = StockBalance.query.filter_by(product_id=test_products[1]).first()
        
        assert balance1 is not None
        assert balance2 is not None
        assert float(balance1.quantity) == 10
        assert float(balance2.quantity) == 5

def test_process_income_document_wrong_type(app, test_products, admin_user):
    """Тест попытки провести расходный документ как приходной"""
    with app.app_context():
        doc = Document(
            doc_type='expense',  # Неправильный тип
            doc_number='INC-TEST-002',
            doc_date=date.today(),
            author_id=admin_user,
            status='draft'
        )
        db.session.add(doc)
        db.session.commit()
        
        with pytest.raises(ValueError, match="только для приходных"):
            StockService.process_income_document(doc)

def test_process_income_document_already_posted(app, test_products, admin_user):
    """Тест попытки провести уже проведенный документ"""
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='INC-TEST-003',
            doc_date=date.today(),
            author_id=admin_user,
            status='posted'  # Уже проведен
        )
        db.session.add(doc)
        db.session.commit()
        
        with pytest.raises(ValueError, match="не в статусе черновика"):
            StockService.process_income_document(doc)

def test_process_expense_document_success(app, test_products, admin_user):
    """Тест успешного проведения расходного документа"""
    with app.app_context():
        # Сначала создаем остатки
        balance1 = StockBalance(
            product_id=test_products[0],
            cell_id=1,
            quantity=20
        )
        balance2 = StockBalance(
            product_id=test_products[1],
            cell_id=1,
            quantity=15
        )
        db.session.add_all([balance1, balance2])
        db.session.commit()
        
        # Создаем расходной документ
        doc = Document(
            doc_type='expense',
            doc_number='EXP-TEST-001',
            doc_date=date.today(),
            author_id=admin_user,
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item1 = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=5,
            price=1000
        )
        item2 = DocumentItem(
            document_id=doc.id,
            product_id=test_products[1],
            quantity=10,
            price=500
        )
        db.session.add_all([item1, item2])
        db.session.commit()
        
        success, message = StockService.process_expense_document(doc)
        
        assert success is True
        assert doc.status == 'posted'
        
        # Проверяем остатки
        new_balance1 = StockBalance.query.filter_by(product_id=test_products[0]).first()
        new_balance2 = StockBalance.query.filter_by(product_id=test_products[1]).first()
        
        assert float(new_balance1.quantity) == 15  # 20 - 5
        assert float(new_balance2.quantity) == 5   # 15 - 10

def test_process_expense_document_insufficient(app, test_products, admin_user):
    """Тест ошибки при недостатке товара"""
    with app.app_context():
        # Создаем маленький остаток
        balance = StockBalance(
            product_id=test_products[0],
            cell_id=1,
            quantity=3
        )
        db.session.add(balance)
        db.session.commit()
        
        doc = Document(
            doc_type='expense',
            doc_number='EXP-TEST-002',
            doc_date=date.today(),
            author_id=admin_user,
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
        
        success, message = StockService.process_expense_document(doc)
        
        assert success is False
        assert 'Недостаточно' in message
        assert doc.status == 'draft'  # Статус не изменился

def test_process_expense_document_no_stock(app, test_products, admin_user):
    """Тест расхода при отсутствии остатков"""
    with app.app_context():
        doc = Document(
            doc_type='expense',
            doc_number='EXP-TEST-003',
            doc_date=date.today(),
            author_id=admin_user,
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=1,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
        
        success, message = StockService.process_expense_document(doc)
        
        assert success is False
        assert 'Недостаточно' in message or 'ошибка' in message.lower()
        assert doc.status == 'draft'

def test_cancel_income_document(app, test_products, admin_user):
    """Тест отмены приходного документа"""
    with app.app_context():
        # Создаем и проводим приход
        doc = Document(
            doc_type='income',
            doc_number='INC-TEST-004',
            doc_date=date.today(),
            author_id=admin_user,
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
        
        StockService.process_income_document(doc)
        
        # Запоминаем остаток до отмены
        before_cancel = StockBalance.query.filter_by(product_id=test_products[0]).first()
        before_qty = float(before_cancel.quantity)
        
        # Отменяем документ
        success, message = StockService.cancel_document(doc)
        
        assert success is True
        assert doc.status == 'cancelled'
        assert doc.cancelled_at is not None
        
        # Проверяем, что остаток уменьшился (товар списался)
        after_cancel = StockBalance.query.filter_by(product_id=test_products[0]).first()
        assert float(after_cancel.quantity) == before_qty - 10

def test_cancel_expense_document(app, test_products, admin_user):
    """Тест отмены расходного документа"""
    with app.app_context():
        # Создаем остаток
        balance = StockBalance(
            product_id=test_products[0],
            cell_id=1,
            quantity=20
        )
        db.session.add(balance)
        db.session.commit()
        
        # Создаем и проводим расход
        doc = Document(
            doc_type='expense',
            doc_number='EXP-TEST-004',
            doc_date=date.today(),
            author_id=admin_user,
            status='draft'
        )
        db.session.add(doc)
        db.session.flush()
        
        item = DocumentItem(
            document_id=doc.id,
            product_id=test_products[0],
            quantity=5,
            price=1000
        )
        db.session.add(item)
        db.session.commit()
        
        StockService.process_expense_document(doc)
        
        # Запоминаем остаток после расхода
        after_expense = StockBalance.query.filter_by(product_id=test_products[0]).first()
        after_qty = float(after_expense.quantity)  # Должно быть 15
        
        # Отменяем документ
        success, message = StockService.cancel_document(doc)
        
        assert success is True
        assert doc.status == 'cancelled'
        
        # Проверяем, что остаток вернулся
        after_cancel = StockBalance.query.filter_by(product_id=test_products[0]).first()
        assert float(after_cancel.quantity) == after_qty + 5  # 15 + 5 = 20

def test_cancel_already_cancelled(app, test_products, admin_user):
    """Тест отмены уже отмененного документа"""
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='INC-TEST-005',
            doc_date=date.today(),
            author_id=admin_user,
            status='cancelled'  # Уже отменен
        )
        db.session.add(doc)
        db.session.commit()
        
        with pytest.raises(ValueError, match="не в статусе"):
            StockService.cancel_document(doc)

def test_cancel_draft_document(app, test_products, admin_user):
    """Тест отмены черновика (должно быть ошибкой)"""
    with app.app_context():
        doc = Document(
            doc_type='income',
            doc_number='INC-TEST-006',
            doc_date=date.today(),
            author_id=admin_user,
            status='draft'  # Черновик
        )
        db.session.add(doc)
        db.session.commit()
        
        with pytest.raises(ValueError, match="не в статусе"):
            StockService.cancel_document(doc)

def test_get_stock_balance_with_filters(app, test_products, test_cells):
    """Тест получения остатков с фильтрацией"""
    with app.app_context():
        # Создаем остатки
        balance1 = StockBalance(
            product_id=test_products[0],
            cell_id=test_cells[0],
            quantity=100
        )
        balance2 = StockBalance(
            product_id=test_products[1],
            cell_id=test_cells[1],
            quantity=50
        )
        balance3 = StockBalance(
            product_id=test_products[0],
            cell_id=test_cells[1],
            quantity=30
        )
        db.session.add_all([balance1, balance2, balance3])
        db.session.commit()
        
        # Фильтр по продукту
        balances = StockService.get_stock_balance(product_id=test_products[0])
        assert len(balances) == 2
        assert all(b.product_id == test_products[0] for b in balances)
        
        # Фильтр по ячейке
        balances = StockService.get_stock_balance(cell_id=test_cells[1])
        assert len(balances) == 2
        assert all(b.cell_id == test_cells[1] for b in balances)
        
        # Фильтр по минимальному количеству
        balances = StockService.get_stock_balance(min_quantity=60)
        assert len(balances) == 1
        assert float(balances[0].quantity) == 100

def test_get_stock_balance_no_filters(app, test_products, test_cells):
    """Тест получения всех остатков без фильтров"""
    with app.app_context():
        # Создаем остатки
        balance1 = StockBalance(
            product_id=test_products[0],
            cell_id=test_cells[0],
            quantity=100
        )
        balance2 = StockBalance(
            product_id=test_products[1],
            cell_id=test_cells[1],
            quantity=50
        )
        db.session.add_all([balance1, balance2])
        db.session.commit()
        
        balances = StockService.get_stock_balance()
        assert len(balances) == 2

def test_get_product_movement(app, test_products, admin_user):
    """Тест получения истории движения товара"""
    with app.app_context():
        product_id = test_products[0]
        
        # Создаем несколько документов
        dates = [
            date(2025, 1, 10),
            date(2025, 1, 15),
            date(2025, 1, 20)
        ]
        
        for i, doc_date in enumerate(dates):
            doc = Document(
                doc_type='income' if i % 2 == 0 else 'expense',
                doc_number=f'TEST-MOV-{i+1}',
                doc_date=doc_date,
                author_id=admin_user,
                status='posted'
            )
            db.session.add(doc)
            db.session.flush()
            
            item = DocumentItem(
                document_id=doc.id,
                product_id=product_id,
                quantity=10,
                price=1000
            )
            db.session.add(item)
        
        db.session.commit()
        
        # Получаем движения
        movements = StockService.get_product_movement(product_id)
        
        assert len(movements) == 3
        assert movements[0]['date'] == dates[0]
        assert movements[1]['date'] == dates[1]
        assert movements[2]['date'] == dates[2]

def test_get_product_movement_with_date_range(app, test_products, admin_user):
    """Тест получения истории движения товара за период"""
    with app.app_context():
        product_id = test_products[0]
        
        # Создаем документы с разными датами
        doc1 = Document(
            doc_type='income',
            doc_number='TEST-MOV-5',
            doc_date=date(2025, 1, 5),
            author_id=admin_user,
            status='posted'
        )
        db.session.add(doc1)
        db.session.flush()
        
        item1 = DocumentItem(
            document_id=doc1.id,
            product_id=product_id,
            quantity=10,
            price=1000
        )
        db.session.add(item1)
        
        doc2 = Document(
            doc_type='income',
            doc_number='TEST-MOV-6',
            doc_date=date(2025, 1, 15),
            author_id=admin_user,
            status='posted'
        )
        db.session.add(doc2)
        db.session.flush()
        
        item2 = DocumentItem(
            document_id=doc2.id,
            product_id=product_id,
            quantity=10,
            price=1000
        )
        db.session.add(item2)
        
        doc3 = Document(
            doc_type='income',
            doc_number='TEST-MOV-7',
            doc_date=date(2025, 1, 25),
            author_id=admin_user,
            status='posted'
        )
        db.session.add(doc3)
        db.session.flush()
        
        item3 = DocumentItem(
            document_id=doc3.id,
            product_id=product_id,
            quantity=10,
            price=1000
        )
        db.session.add(item3)
        
        db.session.commit()
        
        # Фильтр по датам
        movements = StockService.get_product_movement(
            product_id,
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 20)
        )
        
        assert len(movements) == 1
        assert movements[0]['date'] == date(2025, 1, 15)