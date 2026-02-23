from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Document, DocumentItem, Product, Supplier, StockBalance
from app.forms import DocumentForm, DocumentItemForm
from app.services.stock_service import StockService
from datetime import datetime
from sqlalchemy import or_

bp = Blueprint('documents', __name__)

@bp.route('/')
@login_required
def document_list():
    """Список документов"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Фильтрация
    doc_type = request.args.get('type', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Document.query
    
    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        query = query.filter(Document.doc_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Document.doc_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    # Сортировка - сначала новые
    documents = query.order_by(Document.doc_date.desc(), Document.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('documents/list.html',
                          title='Документы',
                          documents=documents,
                          doc_type=doc_type,
                          status=status,
                          date_from=date_from,
                          date_to=date_to)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def document_create():
    """Создание нового документа"""
    if not current_user.is_manager():
        flash('У вас нет прав для создания документов', 'danger')
        return redirect(url_for('documents.document_list'))
    
    form = DocumentForm()
    
    # Заполняем select поля
    form.supplier_id.choices = [(0, '-- Не выбран --')] + [
        (s.id, s.name) for s in Supplier.query.all()
    ]
    
    # Для AJAX-подгрузки товаров в шаблоне
    products = Product.query.all()
    
    if form.validate_on_submit():
        # Генерация номера документа
        today = datetime.now()
        prefix = 'ПН' if form.doc_type.data == 'income' else 'РН'
        count = Document.query.filter(
            Document.doc_number.like(f'{prefix}-{today.strftime("%Y%m")}%')
        ).count() + 1
        doc_number = f"{prefix}-{today.strftime('%Y%m')}-{count:04d}"
        
        document = Document(
            doc_type=form.doc_type.data,
            doc_number=doc_number,
            doc_date=form.doc_date.data,
            supplier_id=form.supplier_id.data if form.supplier_id.data != 0 else None,
            author_id=current_user.id,
            comment=form.comment.data,
            status='draft'
        )
        
        db.session.add(document)
        db.session.flush()  # Чтобы получить id документа
        
        # Добавляем строки документа
        for item_form in form.items.entries:
            if item_form.product_id.data and item_form.quantity.data:
                item = DocumentItem(
                    document_id=document.id,
                    product_id=item_form.product_id.data,
                    quantity=item_form.quantity.data,
                    price=item_form.price.data
                )
                db.session.add(item)
        
        db.session.commit()
        
        flash(f'Документ №{doc_number} создан', 'success')
        return redirect(url_for('documents.document_view', id=document.id))
    
    return render_template('documents/form.html',
                          title='Новый документ',
                          form=form,
                          products=products,
                          edit_mode=False)


@bp.route('/<int:id>')
@login_required
def document_view(id):
    """Просмотр документа"""
    document = Document.query.get_or_404(id)
    
    # Проверка прав (можно смотреть всем)
    return render_template('documents/view.html',
                          title=f'Документ №{document.doc_number}',
                          document=document)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def document_edit(id):
    """Редактирование документа (только черновики)"""
    if not current_user.is_manager():
        flash('У вас нет прав для редактирования документов', 'danger')
        return redirect(url_for('documents.document_list'))
    
    document = Document.query.get_or_404(id)
    
    if not document.is_draft():
        flash('Можно редактировать только документы в статусе "Черновик"', 'danger')
        return redirect(url_for('documents.document_view', id=id))
    
    form = DocumentForm(obj=document)
    
    # Заполняем select поля
    form.supplier_id.choices = [(0, '-- Не выбран --')] + [
        (s.id, s.name) for s in Supplier.query.all()
    ]
    
    # Заполняем строки документа
    if request.method == 'GET':
        # Очищаем существующие записи в форме
        while len(form.items.entries) > 0:
            form.items.pop_entry()
        
        # Добавляем строки из документа
        for item in document.items:
            item_form = DocumentItemForm()
            item_form.product_id = item.product_id
            item_form.quantity = item.quantity
            item_form.price = item.price
            form.items.append_entry(item_form)
    
    products = Product.query.all()
    
    if form.validate_on_submit():
        document.doc_date = form.doc_date.data
        document.supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        document.comment = form.comment.data
        
        # Удаляем старые строки
        DocumentItem.query.filter_by(document_id=document.id).delete()
        
        # Добавляем новые
        for item_form in form.items.entries:
            if item_form.product_id.data and item_form.quantity.data:
                item = DocumentItem(
                    document_id=document.id,
                    product_id=item_form.product_id.data,
                    quantity=item_form.quantity.data,
                    price=item_form.price.data
                )
                db.session.add(item)
        
        db.session.commit()
        
        flash(f'Документ №{document.doc_number} обновлен', 'success')
        return redirect(url_for('documents.document_view', id=id))
    
    return render_template('documents/form.html',
                          title=f'Редактирование: {document.doc_number}',
                          form=form,
                          products=products,
                          document=document,
                          edit_mode=True)


@bp.route('/<int:id>/post', methods=['POST'])
@login_required
def document_post(id):
    """Проведение документа"""
    if not current_user.is_manager():
        flash('У вас нет прав для проведения документов', 'danger')
        return redirect(url_for('documents.document_list'))
    
    document = Document.query.get_or_404(id)
    
    if not document.is_draft():
        flash(f'Документ №{document.doc_number} уже был проведен или отменен', 'danger')
        return redirect(url_for('documents.document_view', id=id))
    
    # Вызываем соответствующий метод сервиса
    if document.doc_type == 'income':
        success, message = StockService.process_income_document(document)
    else:
        success, message = StockService.process_expense_document(document)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('documents.document_view', id=id))


@bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def document_cancel(id):
    """Отмена документа"""
    if not current_user.is_manager():
        flash('У вас нет прав для отмены документов', 'danger')
        return redirect(url_for('documents.document_list'))
    
    document = Document.query.get_or_404(id)
    
    if not document.is_posted():
        flash(f'Можно отменить только проведенный документ', 'danger')
        return redirect(url_for('documents.document_view', id=id))
    
    success, message = StockService.cancel_document(document)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('documents.document_view', id=id))


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def document_delete(id):
    """Удаление документа (только черновики)"""
    if not current_user.is_manager():
        flash('У вас нет прав для удаления документов', 'danger')
        return redirect(url_for('documents.document_list'))
    
    document = Document.query.get_or_404(id)
    
    if not document.is_draft():
        flash('Можно удалить только документы в статусе "Черновик"', 'danger')
        return redirect(url_for('documents.document_view', id=id))
    
    doc_number = document.doc_number
    db.session.delete(document)
    db.session.commit()
    
    flash(f'Документ №{doc_number} удален', 'success')
    return redirect(url_for('documents.document_list'))


# ============== API ДЛЯ AJAX ==============

@bp.route('/api/products/<int:product_id>/price')
@login_required
def api_product_price(product_id):
    """API для получения текущей цены товара"""
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'price': float(product.price)
    })


@bp.route('/api/check-availability')
@login_required
def api_check_availability():
    """API для проверки наличия товара (для расходных документов)"""
    product_id = request.args.get('product_id', type=int)
    quantity = request.args.get('quantity', type=float)
    
    if not product_id or not quantity:
        return jsonify({'available': False, 'message': 'Не указан товар или количество'})
    
    # Считаем общий остаток по товару
    total = db.session.query(db.func.sum(StockBalance.quantity)).filter_by(
        product_id=product_id
    ).scalar() or 0
    
    if total >= quantity:
        return jsonify({
            'available': True,
            'current_stock': float(total),
            'message': f'Достаточно (в наличии: {total})'
        })
    else:
        return jsonify({
            'available': False,
            'current_stock': float(total),
            'message': f'Недостаточно (в наличии: {total})'
        })