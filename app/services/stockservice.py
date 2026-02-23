from app import db
from app.models import StockBalance, Document, DocumentItem, Product, WarehouseCell
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from decimal import Decimal

class StockService:
    """Сервис для управления остатками товаров"""
    
    @staticmethod
    def process_income_document(document):
        """
        Обработка приходного документа:
        - Увеличивает остатки по каждому товару
        - Переводит документ в статус "проведён"
        """
        if document.status != 'draft':
            raise ValueError(f'Документ {document.doc_number} не в статусе черновика')
        
        if document.doc_type != 'income':
            raise ValueError('Метод предназначен только для приходных документов')
        
        try:
            # Начинаем транзакцию
            for item in document.items:
                # Ищем или создаём запись остатка
                balance = StockBalance.query.filter_by(
                    product_id=item.product_id,
                    cell_id=1  # По умолчанию ячейка №1, в реальной системе нужно выбирать
                ).first()
                
                if balance:
                    # Увеличиваем существующий остаток
                    balance.quantity += item.quantity
                else:
                    # Создаём новую запись остатка
                    balance = StockBalance(
                        product_id=item.product_id,
                        cell_id=1,
                        quantity=item.quantity
                    )
                    db.session.add(balance)
            
            # Меняем статус документа
            document.status = 'posted'
            document.posted_at = datetime.utcnow()
            
            db.session.commit()
            return True, "Документ успешно проведён"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при проведении документа: {str(e)}"
    
    @staticmethod
    def process_expense_document(document):
        """
        Обработка расходного документа:
        - Проверяет наличие товара
        - Уменьшает остатки
        - Переводит документ в статус "проведён"
        """
        if document.status != 'draft':
            raise ValueError(f'Документ {document.doc_number} не в статусе черновика')
        
        if document.doc_type != 'expense':
            raise ValueError('Метод предназначен только для расходных документов')
        
        try:
            # Сначала проверяем наличие всех товаров
            for item in document.items:
                balance = StockBalance.query.filter_by(
                    product_id=item.product_id,
                    cell_id=1
                ).first()
                
                if not balance or balance.quantity < item.quantity:
                    product = Product.query.get(item.product_id)
                    available = balance.quantity if balance else 0
                    raise ValueError(
                        f'Недостаточно товара {product.name} (арт. {product.article}). '
                        f'Требуется: {item.quantity}, доступно: {available}'
                    )
            
            # Если всё есть - списываем
            for item in document.items:
                balance = StockBalance.query.filter_by(
                    product_id=item.product_id,
                    cell_id=1
                ).first()
                
                balance.quantity -= item.quantity
            
            # Меняем статус документа
            document.status = 'posted'
            document.posted_at = datetime.utcnow()
            
            db.session.commit()
            return True, "Документ успешно проведён"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при проведении документа: {str(e)}"
    
    @staticmethod
    def cancel_document(document):
        """
        Отмена проведённого документа:
        - Для прихода: уменьшает остатки
        - Для расхода: увеличивает остатки
        """
        if document.status != 'posted':
            raise ValueError(f'Документ {document.doc_number} не в статусе "проведён"')
        
        try:
            if document.doc_type == 'income':
                # Отмена прихода - списываем товары
                for item in document.items:
                    balance = StockBalance.query.filter_by(
                        product_id=item.product_id,
                        cell_id=1
                    ).first()
                    
                    if not balance or balance.quantity < item.quantity:
                        raise ValueError(
                            f'Невозможно отменить документ: недостаточно товара для списания'
                        )
                    
                    balance.quantity -= item.quantity
                    
            else:  # expense
                # Отмена расхода - возвращаем товары
                for item in document.items:
                    balance = StockBalance.query.filter_by(
                        product_id=item.product_id,
                        cell_id=1
                    ).first()
                    
                    if balance:
                        balance.quantity += item.quantity
                    else:
                        # Если записи не было (странно, но вдруг), создаём
                        balance = StockBalance(
                            product_id=item.product_id,
                            cell_id=1,
                            quantity=item.quantity
                        )
                        db.session.add(balance)
            
            document.status = 'cancelled'
            document.cancelled_at = datetime.utcnow()
            
            db.session.commit()
            return True, "Документ успешно отменён"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при отмене документа: {str(e)}"
    
    @staticmethod
    def get_stock_balance(product_id=None, cell_id=None, min_quantity=None):
        """
        Получение остатков с фильтрацией
        """
        query = StockBalance.query
        
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        if cell_id:
            query = query.filter_by(cell_id=cell_id)
        
        balances = query.all()
        
        if min_quantity:
            balances = [b for b in balances if b.quantity >= min_quantity]
        
        return balances
    
    @staticmethod
    def get_product_movement(product_id, start_date=None, end_date=None):
        """
        Получение истории движения товара
        """
        query = DocumentItem.query.filter_by(product_id=product_id)
        
        if start_date:
            query = query.join(Document).filter(Document.doc_date >= start_date)
        
        if end_date:
            query = query.join(Document).filter(Document.doc_date <= end_date)
        
        movements = []
        for item in query.all():
            movements.append({
                'date': item.document.doc_date,
                'doc_number': item.document.doc_number,
                'doc_type': item.document.doc_type,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.quantity * item.price,
                'status': item.document.status
            })
        
        return sorted(movements, key=lambda x: x['date'])