from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Supplier, WarehouseCell, StockBalance
from app.forms import ProductForm, CategoryForm, SupplierForm, WarehouseCellForm, StockFilterForm
from app.services.stock_service import StockService
from sqlalchemy.exc import IntegrityError

bp = Blueprint('products', __name__)

# ============== ТОВАРЫ ==============

@bp.route('/')
@login_required
def product_list():
    """Список товаров"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Фильтрация
    category_id = request.args.get('category_id', type=int)
    supplier_id = request.args.get('supplier_id', type=int)
    search = request.args.get('search', '')
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) | 
            (Product.article.ilike(f'%{search}%'))
        )
    
    # Пагинация
    products = query.order_by(Product.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Для фильтров в шаблоне
    categories = Category.query.all()
    suppliers = Supplier.query.all()
    
    return render_template('products/list.html', 
                          title='Товары',
                          products=products,
                          categories=categories,
                          suppliers=suppliers,
                          selected_category=category_id,
                          selected_supplier=supplier_id,
                          search=search)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def product_create():
    """Создание нового товара"""
    if not current_user.is_manager():
        flash('У вас нет прав для создания товаров', 'danger')
        return redirect(url_for('products.product_list'))
    
    form = ProductForm()
    
    # Заполняем select поля
    form.category_id.choices = [(0, '-- Выберите категорию --')] + [
        (c.id, c.name) for c in Category.query.all()
    ]
    form.supplier_id.choices = [(0, '-- Выберите поставщика --')] + [
        (s.id, s.name) for s in Supplier.query.all()
    ]
    
    if form.validate_on_submit():
        # Проверка уникальности артикула
        if Product.query.filter_by(article=form.article.data).first():
            flash('Товар с таким артикулом уже существует', 'danger')
            return render_template('products/form.html', title='Новый товар', form=form)
        
        product = Product(
            article=form.article.data,
            name=form.name.data,
            unit=form.unit.data,
            price=form.price.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            supplier_id=form.supplier_id.data if form.supplier_id.data != 0 else None
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash(f'Товар "{product.name}" успешно создан', 'success')
        return redirect(url_for('products.product_list'))
    
    return render_template('products/form.html', title='Новый товар', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def product_edit(id):
    """Редактирование товара"""
    if not current_user.is_manager():
        flash('У вас нет прав для редактирования товаров', 'danger')
        return redirect(url_for('products.product_list'))
    
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    
    form.category_id.choices = [(0, '-- Выберите категорию --')] + [
        (c.id, c.name) for c in Category.query.all()
    ]
    form.supplier_id.choices = [(0, '-- Выберите поставщика --')] + [
        (s.id, s.name) for s in Supplier.query.all()
    ]
    
    if form.validate_on_submit():
        # Проверка уникальности артикула (исключая текущий)
        existing = Product.query.filter_by(article=form.article.data).first()
        if existing and existing.id != id:
            flash('Товар с таким артикулом уже существует', 'danger')
            return render_template('products/form.html', title='Редактирование', form=form, product=product)
        
        product.article = form.article.data
        product.name = form.name.data
        product.unit = form.unit.data
        product.price = form.price.data
        product.category_id = form.category_id.data if form.category_id.data != 0 else None
        product.supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        
        db.session.commit()
        
        flash(f'Товар "{product.name}" успешно обновлен', 'success')
        return redirect(url_for('products.product_list'))
    
    return render_template('products/form.html', title='Редактирование', form=form, product=product)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def product_delete(id):
    """Удаление товара"""
    if not current_user.is_manager():
        flash('У вас нет прав для удаления товаров', 'danger')
        return redirect(url_for('products.product_list'))
    
    product = Product.query.get_or_404(id)
    
    try:
        # Проверка, есть ли остатки по товару
        balances = StockBalance.query.filter_by(product_id=id).count()
        if balances > 0:
            flash(f'Нельзя удалить товар "{product.name}" - есть остатки на складе', 'danger')
            return redirect(url_for('products.product_list'))
        
        # Проверка, есть ли движения по товару в документах
        if product.document_items.count() > 0:
            flash(f'Нельзя удалить товар "{product.name}" - есть движения в документах', 'danger')
            return redirect(url_for('products.product_list'))
        
        name = product.name
        db.session.delete(product)
        db.session.commit()
        flash(f'Товар "{name}" удален', 'success')
        
    except IntegrityError as e:
        db.session.rollback()
        flash(f'Ошибка: товар используется в других записях', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    
    return redirect(url_for('products.product_list'))


@bp.route('/<int:id>/movement')
@login_required
def product_movement(id):
    """История движения товара"""
    from app.models import Document, DocumentItem
    
    product = Product.query.get_or_404(id)
    
    # Получаем все движения по товару
    items = DocumentItem.query.filter_by(product_id=id).join(Document).filter(
        Document.status == 'posted'
    ).order_by(Document.doc_date).all()
    
    movements = []
    running_balance = 0
    
    # Считаем бегущий остаток
    for item in items:
        if item.document.doc_type == 'income':
            running_balance += float(item.quantity)
        else:
            running_balance -= float(item.quantity)
        
        movements.append({
            'date': item.document.doc_date,
            'doc_number': item.document.doc_number,
            'doc_type': item.document.doc_type,
            'doc_type_name': 'Приход' if item.document.doc_type == 'income' else 'Расход',
            'quantity': float(item.quantity),
            'price': float(item.price),
            'total': float(item.quantity * item.price),
            'balance': running_balance,
            'supplier': item.document.supplier.name if item.document.supplier else '-'
        })
    
    return render_template('products/movement.html',
                          title=f'Движение: {product.name}',
                          product=product,
                          movements=movements)


# ============== КАТЕГОРИИ ==============

@bp.route('/categories')
@login_required
def category_list():
    """Список категорий"""
    categories = Category.query.all()
    return render_template('products/categories.html', title='Категории', categories=categories)


@bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
def category_create():
    """Создание категории"""
    if not current_user.is_manager():
        flash('У вас нет прав для создания категорий', 'danger')
        return redirect(url_for('products.category_list'))
    
    form = CategoryForm()
    if form.validate_on_submit():
        # Проверка уникальности
        if Category.query.filter_by(name=form.name.data).first():
            flash('Категория с таким названием уже существует', 'danger')
            return render_template('products/category_form.html', title='Новая категория', form=form)
        
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash(f'Категория "{category.name}" создана', 'success')
        return redirect(url_for('products.category_list'))
    
    return render_template('products/category_form.html', title='Новая категория', form=form)


@bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def category_edit(id):
    """Редактирование категории"""
    if not current_user.is_manager():
        flash('У вас нет прав для редактирования категорий', 'danger')
        return redirect(url_for('products.category_list'))
    
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        # Проверка уникальности (исключая текущую)
        existing = Category.query.filter_by(name=form.name.data).first()
        if existing and existing.id != id:
            flash('Категория с таким названием уже существует', 'danger')
            return render_template('products/category_form.html', title='Редактирование', form=form, category=category)
        
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        
        flash(f'Категория "{category.name}" обновлена', 'success')
        return redirect(url_for('products.category_list'))
    
    return render_template('products/category_form.html', title='Редактирование', form=form, category=category)


@bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def category_delete(id):
    """Удаление категории"""
    if not current_user.is_manager():
        flash('У вас нет прав для удаления категорий', 'danger')
        return redirect(url_for('products.category_list'))
    
    category = Category.query.get_or_404(id)
    
    # Проверка, есть ли товары в этой категории
    if category.products.count() > 0:
        flash('Нельзя удалить категорию, в которой есть товары', 'danger')
        return redirect(url_for('products.category_list'))
    
    name = category.name
    db.session.delete(category)
    db.session.commit()
    
    flash(f'Категория "{name}" удалена', 'success')
    return redirect(url_for('products.category_list'))


# ============== ПОСТАВЩИКИ ==============

@bp.route('/suppliers')
@login_required
def supplier_list():
    """Список поставщиков"""
    suppliers = Supplier.query.all()
    return render_template('products/suppliers.html', title='Поставщики', suppliers=suppliers)


@bp.route('/suppliers/create', methods=['GET', 'POST'])
@login_required
def supplier_create():
    """Создание поставщика"""
    if not current_user.is_manager():
        flash('У вас нет прав для создания поставщиков', 'danger')
        return redirect(url_for('products.supplier_list'))
    
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            inn=form.inn.data,
            contact_person=form.contact_person.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        flash(f'Поставщик "{supplier.name}" создан', 'success')
        return redirect(url_for('products.supplier_list'))
    
    return render_template('products/supplier_form.html', title='Новый поставщик', form=form)


@bp.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def supplier_edit(id):
    """Редактирование поставщика"""
    if not current_user.is_manager():
        flash('У вас нет прав для редактирования поставщиков', 'danger')
        return redirect(url_for('products.supplier_list'))
    
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    
    if form.validate_on_submit():
        supplier.name = form.name.data
        supplier.inn = form.inn.data
        supplier.contact_person = form.contact_person.data
        supplier.phone = form.phone.data
        supplier.email = form.email.data
        supplier.address = form.address.data
        
        db.session.commit()
        
        flash(f'Поставщик "{supplier.name}" обновлен', 'success')
        return redirect(url_for('products.supplier_list'))
    
    return render_template('products/supplier_form.html', title='Редактирование', form=form, supplier=supplier)


@bp.route('/suppliers/<int:id>/delete', methods=['POST'])
@login_required
def supplier_delete(id):
    """Удаление поставщика"""
    if not current_user.is_manager():
        flash('У вас нет прав для удаления поставщиков', 'danger')
        return redirect(url_for('products.supplier_list'))
    
    supplier = Supplier.query.get_or_404(id)
    
    # Проверка, есть ли товары этого поставщика
    if supplier.products.count() > 0:
        flash('Нельзя удалить поставщика, у которого есть товары', 'danger')
        return redirect(url_for('products.supplier_list'))
    
    name = supplier.name
    db.session.delete(supplier)
    db.session.commit()
    
    flash(f'Поставщик "{name}" удален', 'success')
    return redirect(url_for('products.supplier_list'))


# ============== СКЛАДСКИЕ ЯЧЕЙКИ ==============

@bp.route('/cells')
@login_required
def cell_list():
    """Список ячеек"""
    cells = WarehouseCell.query.all()
    return render_template('products/cells.html', title='Складские ячейки', cells=cells)


@bp.route('/cells/create', methods=['GET', 'POST'])
@login_required
def cell_create():
    """Создание ячейки"""
    if not current_user.is_manager():
        flash('У вас нет прав для создания ячеек', 'danger')
        return redirect(url_for('products.cell_list'))
    
    form = WarehouseCellForm()
    if form.validate_on_submit():
        # Проверка уникальности
        if WarehouseCell.query.filter_by(name=form.name.data).first():
            flash('Ячейка с таким номером уже существует', 'danger')
            return render_template('products/cell_form.html', title='Новая ячейка', form=form)
        
        cell = WarehouseCell(
            name=form.name.data,
            description=form.description.data
        )
        
        db.session.add(cell)
        db.session.commit()
        
        flash(f'Ячейка "{cell.name}" создана', 'success')
        return redirect(url_for('products.cell_list'))
    
    return render_template('products/cell_form.html', title='Новая ячейка', form=form)


@bp.route('/cells/<int:id>/delete', methods=['POST'])
@login_required
def cell_delete(id):
    """Удаление ячейки"""
    if not current_user.is_manager():
        flash('У вас нет прав для удаления ячеек', 'danger')
        return redirect(url_for('products.cell_list'))
    
    cell = WarehouseCell.query.get_or_404(id)
    
    # Проверка, есть ли остатки в этой ячейке
    if cell.balances.count() > 0:
        flash('Нельзя удалить ячейку, в которой есть товары', 'danger')
        return redirect(url_for('products.cell_list'))
    
    name = cell.name
    db.session.delete(cell)
    db.session.commit()
    
    flash(f'Ячейка "{name}" удалена', 'success')
    return redirect(url_for('products.cell_list'))


# ============== ОСТАТКИ ==============

@bp.route('/stock')
@login_required
def stock_balance():
    """Просмотр остатков"""
    form = StockFilterForm()
    
    # Заполняем select поля
    form.product_id.choices = [(0, '-- Все товары --')] + [
        (p.id, f"{p.article} - {p.name}") for p in Product.query.all()
    ]
    form.cell_id.choices = [(0, '-- Все ячейки --')] + [
        (c.id, c.name) for c in WarehouseCell.query.all()
    ]
    
    # Получаем параметры фильтрации из GET
    product_id = request.args.get('product_id', 0, type=int)
    cell_id = request.args.get('cell_id', 0, type=int)
    min_quantity = request.args.get('min_quantity', type=float)
    
    query = StockBalance.query
    
    if product_id and product_id != 0:
        query = query.filter_by(product_id=product_id)
    
    if cell_id and cell_id != 0:
        query = query.filter_by(cell_id=cell_id)
    
    balances = query.all()
    
    if min_quantity:
        balances = [b for b in balances if b.quantity >= min_quantity]
    
    return render_template('products/stock.html',
                          title='Остатки товаров',
                          balances=balances,
                          form=form,
                          product_id=product_id,
                          cell_id=cell_id,
                          min_quantity=min_quantity)