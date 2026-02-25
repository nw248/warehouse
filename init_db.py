from app import create_app, db
from app.models import User, Category, Supplier, WarehouseCell

app = create_app()

with app.app_context():
    # Создаем таблицы
    db.create_all()
    print("Таблицы созданы!")
    
    # Создаем тестовые ячейки
    cells = ['A-01', 'A-02', 'A-03', 'B-01', 'B-02', 'C-01']
    for cell_name in cells:
        if not WarehouseCell.query.filter_by(name=cell_name).first():
            cell = WarehouseCell(name=cell_name, description=f"Ячейка {cell_name}")
            db.session.add(cell)
            print(f"Добавлена ячейка: {cell_name}")
    
    # Создаем тестовые категории - ЗАМЕНИЛИ "Крепеж" на "Строительные материалы"
    categories = ['Электроинструмент', 'Ручной инструмент', 'Строительные материалы']
    for cat_name in categories:
        if not Category.query.filter_by(name=cat_name).first():
            cat = Category(name=cat_name, description=f"Категория {cat_name}")
            db.session.add(cat)
            print(f"Добавлена категория: {cat_name}")
    
    # Создаем тестового поставщика
    if not Supplier.query.first():
        supplier = Supplier(
            name='ООО "ТехноСнаб"',
            inn='7701234567',
            contact_person='Иванов Иван',
            phone='+7 (495) 123-45-67',
            email='info@tehnosnab.ru',
            address='г. Москва, ул. Строителей, 10'
        )
        db.session.add(supplier)
        print("Добавлен поставщик: ООО ТехноСнаб")
    
    # Создаем администратора
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            full_name='Администратор',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("Добавлен пользователь: admin")
    
    # Создаем тестового менеджера
    if not User.query.filter_by(username='manager').first():
        manager = User(
            username='manager',
            email='manager@example.com',
            full_name='Менеджер',
            role='manager'
        )
        manager.set_password('manager123')
        db.session.add(manager)
        print("Добавлен пользователь: manager")
    
    # Создаем тестового кладовщика
    if not User.query.filter_by(username='storekeeper').first():
        storekeeper = User(
            username='storekeeper',
            email='storekeeper@example.com',
            full_name='Кладовщик',
            role='storekeeper'
        )
        storekeeper.set_password('storekeeper123')
        db.session.add(storekeeper)
        print("Добавлен пользователь: storekeeper")
    
    db.session.commit()
    print("=" * 50)
    print("✅ База данных успешно инициализирована!")
    print("=" * 50)
    print("Категории товаров:")
    for cat_name in categories:
        print(f"  • {cat_name}")
    print("=" * 50)
    print("Вход в систему:")
    print("  admin / admin123 - Администратор")
    print("  manager / manager123 - Менеджер")
    print("  storekeeper / storekeeper123 - Кладовщик")
    print("=" * 50)