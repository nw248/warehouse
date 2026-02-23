from app.services import create_app, db
from app.models import User, Category, Supplier, WarehouseCell

app = create_app()

with app.app_context():
    db.create_all()
    
    # Ячейки
    cells = ['A-01', 'A-02', 'A-03', 'B-01', 'B-02']
    for cell_name in cells:
        if not WarehouseCell.query.filter_by(name=cell_name).first():
            db.session.add(WarehouseCell(name=cell_name))
    
    # Категории
    categories = ['Электроинструмент', 'Ручной инструмент', 'Крепеж']
    for cat_name in categories:
        if not Category.query.filter_by(name=cat_name).first():
            db.session.add(Category(name=cat_name))
    
    # Поставщик
    if not Supplier.query.first():
        db.session.add(Supplier(name='ООО "ТехноСнаб"', inn='7701234567'))
    
    # Администратор
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', 
                    full_name='Администратор', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
    
    db.session.commit()
    print("База данных инициализирована!")