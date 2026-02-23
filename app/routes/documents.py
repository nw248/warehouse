from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Document, DocumentItem, Product, Supplier
from app.forms import DocumentForm
from app.services.stock_service import StockService
from datetime import datetime

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
    form.supplier_id.choices = [(0, '-- Не выбран --')] + [
        (s.id, s.name) for s in Supplier.query.all()
    ]
    
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
        db.session.flush()
        
        # Обрабатываем 5 фиксированных строк
        has_items = False
        for i in range(5):
            product_id = request.form.get(f'product_{i}', type=int)
            quantity = request.form.get(f'quantity_{i}', type=float)
            price = request.form.get(f'price_{i}', type=float)
            
            if product_id and quantity and quantity > 0:
                item = DocumentItem(
                    document_id=document.id,
                    product_id=product_id,
                    quantity=quantity,
                    price=price
                )
                db.session.add(item)
                has_items = True
        
        if not has_items:
            db.session.rollback()
            flash('Добавьте хотя бы один товар в документ', 'danger')
            return render_template('documents/form.html',
                                  title='Новый документ',
                                  form=form,
                                  products=Product.query.all(),
                                  edit_mode=False)
        
        db.session.commit()
        flash(f'Документ №{doc_number} создан', 'success')
        return redirect(url_for('documents.document_view', id=document.id))
    
    return render_template('documents/form.html',
                          title='Новый документ',
                          form=form,
                          products=Product.query.all(),
                          edit_mode=False)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def document_edit(id):
    """Редактирование документа"""
    if not current_user.is_manager():
        flash('У вас нет прав для редактирования документов', 'danger')
        return redirect(url_for('documents.document_list'))
    
    document = Document.query.get_or_404(id)
    
    if not document.is_draft():
        flash('Можно редактировать только документы в статусе "Черновик"', 'danger')
        return redirect(url_for('documents.document_view', id=id))
    
    form = DocumentForm(obj=document)
    form.supplier_id.choices = [(0, '-- Не выбран --')] + [
        (s.id, s.name) for s in Supplier.query.all()
    ]
    
    if form.validate_on_submit():
        document.doc_date = form.doc_date.data
        document.supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        document.comment = form.comment.data
        
        # Удаляем старые строки
        DocumentItem.query.filter_by(document_id=document.id).delete()
        
        # Добавляем новые из формы
        has_items = False
        for i in range(5):
            product_id = request.form.get(f'product_{i}', type=int)
            quantity = request.form.get(f'quantity_{i}', type=float)
            price = request.form.get(f'price_{i}', type=float)
            
            if product_id and quantity and quantity > 0:
                item = DocumentItem(
                    document_id=document.id,
                    product_id=product_id,
                    quantity=quantity,
                    price=price
                )
                db.session.add(item)
                has_items = True
        
        if not has_items:
            flash('Добавьте хотя бы один товар в документ', 'danger')
            return redirect(url_for('documents.document_edit', id=id))
        
        db.session.commit()
        flash(f'Документ №{document.doc_number} обновлен', 'success')
        return redirect(url_for('documents.document_view', id=id))
    
    return render_template('documents/form.html',
                          title=f'Редактирование: {document.doc_number}',
                          form=form,
                          products=Product.query.all(),
                          document=document,
                          edit_mode=True)


@bp.route('/<int:id>')
@login_required
def document_view(id):
    """Просмотр документа"""
    document = Document.query.get_or_404(id)
    return render_template('documents/view.html',
                          title=f'Документ №{document.doc_number}',
                          document=document)


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
    """Удаление документа"""
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