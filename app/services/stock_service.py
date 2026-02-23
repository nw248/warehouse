from app import db
from app.models import StockBalance, Document, DocumentItem, Product
from datetime import datetime
from decimal import Decimal

class StockService:
    """Сервис для управления остатками товаров"""
    
    @staticmethod
    def process_income_document(document):
        """
        Обработка приходного документа:
        - Увеличивает остатки по каждому товару
        """
        if document.status != 'draft':
            raise ValueError(f'Документ {document.doc_number} не в статусе черновика')
        
        if document.doc_type != 'income':
            raise ValueError('Метод предназначен только для приходных документов')
        
        try:
            for item in document.items:
                # Ищем или создаём запись остатка
                balance = StockBalance.query.filter_by(
                    product_id=item.product_id,
                    cell_id=1  # По умолчанию ячейка №1
                ).first()
                
                if balance:
                    balance.quantity += item.quantity
                else:
                    balance = StockBalance(
                        product_id=item.product_id,
                        cell_id=1,
                        quantity=item.quantity
                    )
                    db.session.add(balance)
            
            document.status = 'posted'
            document.posted_at = datetime.utcnow()
            db.session.commit()
            return True, "Документ успешно проведён"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка: {str(e)}"
    
    @staticmethod
    def process_expense_document(document):
        """
        Обработка расходного документа:
        - Проверяет наличие и уменьшает остатки
        """
        if document.status != 'draft':
            raise ValueError(f'Документ {document.doc_number} не в статусе черновика')
        
        if document.doc_type != 'expense':
            raise ValueError('Метод предназначен только для расходных документов')
        
        try:
            # Проверка наличия
            for item in document.items:
                balance = StockBalance.query.filter_by(
                    product_id=item.product_id,
                    cell_id=1
                ).first()
                
                if not balance or balance.quantity < item.quantity:
                    product = Product.query.get(item.product_id)
                    available = balance.quantity if balance else 0
                    raise ValueError(
                        f'Недостаточно товара {product.name}. '
                        f'Требуется: {item.quantity}, доступно: {available}'
                    )
            
            # Списание
            for item in document.items:
                balance = StockBalance.query.filter_by(
                    product_id=item.product_id,
                    cell_id=1
                ).first()
                balance.quantity -= item.quantity
            
            document.status = 'posted'
            document.posted_at = datetime.utcnow()
            db.session.commit()
            return True, "Документ успешно проведён"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка: {str(e)}"
    
    @staticmethod
    def cancel_document(document):
        """Отмена проведённого документа"""
        if document.status != 'posted':
            raise ValueError(f'Документ не в статусе "проведён"')
        
        try:
            if document.doc_type == 'income':
                # Отмена прихода - списываем
                for item in document.items:
                    balance = StockBalance.query.filter_by(
                        product_id=item.product_id,
                        cell_id=1
                    ).first()
                    if balance:
                        balance.quantity -= item.quantity
            else:
                # Отмена расхода - возвращаем
                for item in document.items:
                    balance = StockBalance.query.filter_by(
                        product_id=item.product_id,
                        cell_id=1
                    ).first()
                    if balance:
                        balance.quantity += item.quantity
                    else:
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
            return False, f"Ошибка: {str(e)}"