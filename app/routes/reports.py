from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Supplier, Document, DocumentItem, StockBalance
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import csv
import io
from decimal import Decimal

bp = Blueprint('reports', __name__)

@bp.route('/stock')
@login_required
def stock_report():
    """Отчет по остаткам товаров"""
    # Получаем все товары с остатками
    products = Product.query.all()
    
    report_data = []
    for product in products:
        # Суммарный остаток по всем ячейкам
        total = db.session.query(func.sum(StockBalance.quantity)).filter_by(
            product_id=product.id
        ).scalar() or 0
        
        if total > 0:  # Только товары в наличии
            report_data.append({
                'id': product.id,
                'article': product.article,
                'name': product.name,
                'category': product.category.name if product.category else '-',
                'unit': product.unit,
                'total_quantity': float(total),
                'avg_price': float(product.price),
                'total_value': float(total * product.price)
            })
    
    # Сортировка по категории и названию
    report_data.sort(key=lambda x: (x['category'], x['name']))
    
    # Итоги
    total_items = len(report_data)
    total_quantity = sum(item['total_quantity'] for item in report_data)
    total_value = sum(item['total_value'] for item in report_data)
    
    return render_template('reports/stock.html',
                          title='Отчет по остаткам',
                          report_data=report_data,
                          total_items=total_items,
                          total_quantity=total_quantity,
                          total_value=total_value,
                          generated_at=datetime.now())


@bp.route('/turnover')
@login_required
def turnover_report():
    """Отчет по обороту товаров за период"""
    # Параметры отчета
    period = request.args.get('period', 'month')  # week, month, quarter, year
    category_id = request.args.get('category_id', 0, type=int)
    
    # Определяем дату начала
    today = datetime.now().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    # Базовый запрос
    query = db.session.query(
        Product.id,
        Product.article,
        Product.name,
        Category.name.label('category_name'),
        Product.unit,
        func.sum(DocumentItem.quantity).label('total_quantity'),
        func.sum(DocumentItem.quantity * DocumentItem.price).label('total_sum'),
        func.count(DocumentItem.id).label('operations_count')
    ).join(DocumentItem, Product.id == DocumentItem.product_id
    ).join(Document, DocumentItem.document_id == Document.id
    ).join(Category, Product.category_id == Category.id, isouter=True
    ).filter(Document.doc_date >= start_date
    ).filter(Document.status == 'posted'  # Только проведенные
    )
    
    # Фильтр по категории
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # Группировка
    query = query.group_by(Product.id, Category.name).order_by(Product.name)
    
    report_data = []
    for row in query.all():
        report_data.append({
            'id': row.id,
            'article': row.article,
            'name': row.name,
            'category': row.category_name or '-',
            'unit': row.unit,
            'total_quantity': float(row.total_quantity or 0),
            'total_sum': float(row.total_sum or 0),
            'operations_count': row.operations_count
        })
    
    # Категории для фильтра
    categories = Category.query.all()
    
    # Итоги
    total_operations = sum(item['operations_count'] for item in report_data)
    total_quantity = sum(item['total_quantity'] for item in report_data)
    total_sum = sum(item['total_sum'] for item in report_data)
    
    return render_template('reports/turnover.html',
                          title='Отчет по обороту',
                          report_data=report_data,
                          categories=categories,
                          selected_category=category_id,
                          period=period,
                          start_date=start_date,
                          total_operations=total_operations,
                          total_quantity=total_quantity,
                          total_sum=total_sum,
                          generated_at=datetime.now())


@bp.route('/suppliers')
@login_required
def suppliers_report():
    """Отчет по поставщикам"""
    suppliers = Supplier.query.all()
    
    report_data = []
    for supplier in suppliers:
        # Количество товаров от этого поставщика
        products_count = supplier.products.count()
        
        # Сумма закупок за последний год
        year_ago = datetime.now().date() - timedelta(days=365)
        purchases = db.session.query(
            func.sum(DocumentItem.quantity * DocumentItem.price)
        ).join(Document, DocumentItem.document_id == Document.id
        ).filter(Document.supplier_id == supplier.id
        ).filter(Document.doc_type == 'income'
        ).filter(Document.status == 'posted'
        ).filter(Document.doc_date >= year_ago
        ).scalar() or 0
        
        # Количество поставок за год
        deliveries = Document.query.filter_by(
            supplier_id=supplier.id,
            doc_type='income',
            status='posted'
        ).filter(Document.doc_date >= year_ago).count()
        
        report_data.append({
            'id': supplier.id,
            'name': supplier.name,
            'inn': supplier.inn or '-',
            'contact': supplier.contact_person or '-',
            'phone': supplier.phone or '-',
            'products_count': products_count,
            'deliveries_count': deliveries,
            'total_purchases': float(purchases)
        })
    
    # Сортировка по сумме закупок (убывание)
    report_data.sort(key=lambda x: x['total_purchases'], reverse=True)
    
    # Итоги
    total_suppliers = len(report_data)
    total_products = sum(item['products_count'] for item in report_data)
    total_purchases = sum(item['total_purchases'] for item in report_data)
    
    return render_template('reports/suppliers.html',
                          title='Отчет по поставщикам',
                          report_data=report_data,
                          total_suppliers=total_suppliers,
                          total_products=total_products,
                          total_purchases=total_purchases,
                          generated_at=datetime.now())


@bp.route('/movement/<int:product_id>')
@login_required
def product_movement(product_id):
    """Детальный отчет по движению конкретного товара"""
    product = Product.query.get_or_404(product_id)
    
    # Параметры фильтрации
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = DocumentItem.query.filter_by(product_id=product_id).join(Document)
    
    if date_from:
        query = query.filter(Document.doc_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Document.doc_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    # Получаем все движения
    movements = []
    running_balance = 0
    
    # Сначала получаем начальный остаток на дату начала (если указана)
    if date_from:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        # Считаем остаток на начало периода
        initial = db.session.query(func.sum(StockBalance.quantity)).filter_by(
            product_id=product_id
        ).scalar() or 0
        
        # Вычитаем движения до начальной даты
        before = db.session.query(
            func.sum(DocumentItem.quantity)
        ).join(Document
        ).filter(
            DocumentItem.product_id == product_id,
            Document.doc_date < start_date,
            Document.status == 'posted'
        ).scalar() or 0
        
        running_balance = float(initial) - float(before)
    
    for item in query.order_by(Document.doc_date, Document.id).all():
        if item.document.status != 'posted':
            continue
            
        # Обновляем бегущий остаток
        if item.document.doc_type == 'income':
            running_balance += float(item.quantity)
        else:
            running_balance -= float(item.quantity)
        
        # ВАЖНО: добавляем поле document_id или id документа
        movements.append({
            'date': item.document.doc_date,
            'doc_number': item.document.doc_number,
            'doc_id': item.document.id,  # Это поле нужно для ссылки
            'document_id': item.document.id,  # Добавим еще и так для надежности
            'doc_type': item.document.doc_type,
            'doc_type_name': 'Приход' if item.document.doc_type == 'income' else 'Расход',
            'quantity': float(item.quantity),
            'price': float(item.price),
            'total': float(item.quantity * item.price),
            'balance': running_balance,
            'supplier': item.document.supplier.name if item.document.supplier else '-'
        })
    
    # Отладка - выведем первый элемент, чтобы увидеть структуру
    if movements:
        print("Первый элемент movements:", movements[0].keys())
    
    return render_template('reports/movement.html',
                          title=f'Движение товара: {product.name}',
                          product=product,
                          movements=movements,
                          date_from=date_from,
                          date_to=date_to)


# ============== ЭКСПОРТ В CSV ==============

@bp.route('/export/stock')
@login_required
def export_stock():
    """Экспорт остатков в CSV"""
    # Создаем файл в памяти
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Заголовки
    writer.writerow(['Артикул', 'Наименование', 'Категория', 'Ед.изм.', 
                     'Количество', 'Цена', 'Сумма'])
    
    # Данные
    products = Product.query.all()
    for product in products:
        total = db.session.query(func.sum(StockBalance.quantity)).filter_by(
            product_id=product.id
        ).scalar() or 0
        
        if total > 0:
            writer.writerow([
                product.article,
                product.name,
                product.category.name if product.category else '-',
                product.unit,
                float(total),
                float(product.price),
                float(total * product.price)
            ])
    
    # Подготовка ответа
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('cp1251')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'ostaatki_{datetime.now().strftime("%Y%m%d")}.csv'
    )


@bp.route('/export/turnover')
@login_required
def export_turnover():
    """Экспорт оборота в CSV"""
    period = request.args.get('period', 'month')
    
    # Определяем дату начала (как в turnover_report)
    today = datetime.now().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    # Запрос данных (аналогично turnover_report)
    query = db.session.query(
        Product.article,
        Product.name,
        Category.name.label('category'),
        Product.unit,
        func.sum(DocumentItem.quantity).label('total_qty'),
        func.sum(DocumentItem.quantity * DocumentItem.price).label('total_sum'),
        func.count(DocumentItem.id).label('ops')
    ).join(DocumentItem
    ).join(Document
    ).join(Category, isouter=True
    ).filter(
        Document.doc_date >= start_date,
        Document.status == 'posted'
    ).group_by(Product.id, Category.name).order_by(Product.name)
    
    # Создаем CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    writer.writerow(['Артикул', 'Наименование', 'Категория', 'Ед.изм.',
                     'Кол-во', 'Сумма', 'Кол-во операций'])
    
    for row in query.all():
        writer.writerow([
            row.article,
            row.name,
            row.category or '-',
            row.unit,
            float(row.total_qty or 0),
            float(row.total_sum or 0),
            row.ops
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('cp1251')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'oborot_{period}_{datetime.now().strftime("%Y%m%d")}.csv'
    )


# ============== API ДЛЯ ГРАФИКОВ ==============

@bp.route('/api/chart/turnover')
@login_required
def api_turnover_chart():
    """API для данных графика оборота"""
    period = request.args.get('period', 'month')
    
    # Группировка по дням/неделям/месяцам
    if period == 'week':
        # По дням
        data = db.session.query(
            Document.doc_date,
            func.sum(DocumentItem.quantity * DocumentItem.price).label('total')
        ).join(DocumentItem
        ).filter(Document.status == 'posted'
        ).group_by(Document.doc_date
        ).order_by(Document.doc_date).limit(7).all()
        
        labels = [d.doc_date.strftime('%d.%m') for d in data]
        values = [float(d.total) for d in data]
        
    elif period == 'month':
        # По неделям (упрощенно)
        data = db.session.query(
            extract('week', Document.doc_date).label('week'),
            func.sum(DocumentItem.quantity * DocumentItem.price).label('total')
        ).join(DocumentItem
        ).filter(Document.status == 'posted'
        ).group_by('week'
        ).order_by('week').limit(4).all()
        
        labels = [f'Неделя {int(d.week)}' for d in data]
        values = [float(d.total) for d in data]
        
    else:
        # По месяцам
        data = db.session.query(
            extract('month', Document.doc_date).label('month'),
            func.sum(DocumentItem.quantity * DocumentItem.price).label('total')
        ).join(DocumentItem
        ).filter(Document.status == 'posted'
        ).group_by('month'
        ).order_by('month').limit(12).all()
        
        months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                  'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        labels = [months[int(d.month)-1] for d in data]
        values = [float(d.total) for d in data]
    
    return jsonify({
        'labels': labels,
        'values': values
    })