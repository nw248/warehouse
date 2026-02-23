from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='manager')  # admin, manager, storekeeper
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    documents_created = db.relationship('Document', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    def __repr__(self):
        return f'<User {self.username}>'


class Supplier(db.Model):
    """Модель поставщика"""
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    inn = db.Column(db.String(12), unique=True)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    products = db.relationship('Product', backref='supplier', lazy='dynamic')
    documents = db.relationship('Document', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f'<Supplier {self.name}>'


class Category(db.Model):
    """Модель категории товаров"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    
    # Связи
    products = db.relationship('Product', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    """Модель товара"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='шт')  # шт, кг, м
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    # Внешние ключи
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    balances = db.relationship('StockBalance', backref='product', lazy='dynamic')
    document_items = db.relationship('DocumentItem', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f'<Product {self.article}: {self.name}>'


class WarehouseCell(db.Model):
    """Модель складской ячейки"""
    __tablename__ = 'warehouse_cells'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # A-01, B-12 и т.д.
    description = db.Column(db.String(100))
    
    # Связи
    balances = db.relationship('StockBalance', backref='cell', lazy='dynamic')
    
    def __repr__(self):
        return f'<Cell {self.name}>'


class StockBalance(db.Model):
    """Модель остатков товаров"""
    __tablename__ = 'stock_balances'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Внешние ключи
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    cell_id = db.Column(db.Integer, db.ForeignKey('warehouse_cells.id'), nullable=False)
    
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Уникальность: один товар в одной ячейке
    __table_args__ = (db.UniqueConstraint('product_id', 'cell_id', name='unique_product_cell'),)
    
    def __repr__(self):
        return f'<Balance {self.product_id} in {self.cell_id}: {self.quantity}>'


class Document(db.Model):
    """Модель документа (приход/расход)"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(10), nullable=False)  # income, expense
    doc_number = db.Column(db.String(20), unique=True, nullable=False)
    doc_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Статусы: draft, posted, cancelled
    status = db.Column(db.String(20), nullable=False, default='draft')
    
    # Внешние ключи
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posted_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Комментарий
    comment = db.Column(db.String(500))
    
    # Связи
    items = db.relationship('DocumentItem', backref='document', lazy='dynamic', 
                           cascade='all, delete-orphan')
    
    def total_amount(self):
        """Расчет общей суммы документа"""
        total = 0
        for item in self.items:
            total += item.quantity * item.price
        return total
    
    def is_draft(self):
        return self.status == 'draft'
    
    def is_posted(self):
        return self.status == 'posted'
    
    def __repr__(self):
        return f'<Document {self.doc_number}: {self.doc_type}>'


class DocumentItem(db.Model):
    """Модель строки документа"""
    __tablename__ = 'document_items'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Внешние ключи
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Цена на момент документа
    
    def total(self):
        return self.quantity * self.price
    
    def __repr__(self):
        return f'<Item {self.product_id}: {self.quantity}>'