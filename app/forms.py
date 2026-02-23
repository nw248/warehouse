from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FloatField, IntegerField, DateField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional
from datetime import date

class LoginForm(FlaskForm):
    """Форма входа"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class UserForm(FlaskForm):
    """Форма создания/редактирования пользователя"""
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль', 
                              validators=[DataRequired(), EqualTo('password')])
    full_name = StringField('Полное имя', validators=[DataRequired()])
    role = SelectField('Роль', choices=[
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('storekeeper', 'Кладовщик')
    ], validators=[DataRequired()])
    submit = SubmitField('Сохранить')


class SupplierForm(FlaskForm):
    """Форма поставщика"""
    name = StringField('Наименование', validators=[DataRequired(), Length(max=100)])
    inn = StringField('ИНН', validators=[Length(max=12)])
    contact_person = StringField('Контактное лицо', validators=[Length(max=100)])
    phone = StringField('Телефон', validators=[Length(max=20)])
    email = StringField('Email', validators=[Email(), Length(max=120)])
    address = TextAreaField('Адрес', validators=[Length(max=200)])
    submit = SubmitField('Сохранить')


class CategoryForm(FlaskForm):
    """Форма категории"""
    name = StringField('Название категории', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Описание', validators=[Length(max=200)])
    submit = SubmitField('Сохранить')


class ProductForm(FlaskForm):
    """Форма товара"""
    article = StringField('Артикул', validators=[DataRequired(), Length(max=50)])
    name = StringField('Наименование', validators=[DataRequired(), Length(max=200)])
    unit = SelectField('Единица измерения', choices=[
        ('шт', 'Штука'),
        ('кг', 'Килограмм'),
        ('м', 'Метр'),
        ('уп', 'Упаковка'),
        ('л', 'Литр')
    ], validators=[DataRequired()])
    price = FloatField('Цена', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()], choices=[])
    supplier_id = SelectField('Поставщик', coerce=int, validators=[DataRequired()], choices=[])
    submit = SubmitField('Сохранить')


class WarehouseCellForm(FlaskForm):
    """Форма складской ячейки"""
    name = StringField('Номер ячейки', validators=[DataRequired(), Length(max=20)])
    description = StringField('Описание', validators=[Length(max=100)])
    submit = SubmitField('Сохранить')


class DocumentItemForm(FlaskForm):
    """Форма строки документа (используется внутри DocumentForm)"""
    product_id = SelectField('Товар', coerce=int, validators=[DataRequired()], choices=[])
    quantity = FloatField('Количество', validators=[DataRequired(), NumberRange(min=0.01)])
    price = FloatField('Цена', validators=[DataRequired(), NumberRange(min=0)])


class DocumentForm(FlaskForm):
    """Форма документа (приход/расход)"""
    doc_type = SelectField('Тип документа', choices=[
        ('income', 'Приходная накладная'),
        ('expense', 'Расходная накладная')
    ], validators=[DataRequired()])
    doc_date = DateField('Дата документа', default=date.today, validators=[DataRequired()])
    supplier_id = SelectField('Поставщик/Контрагент', coerce=int, validators=[Optional()], choices=[])
    comment = TextAreaField('Комментарий', validators=[Length(max=500)])
    
    # Динамический список товаров
    items = FieldList(FormField(DocumentItemForm), min_entries=1)
    
    submit = SubmitField('Сохранить')


class StockFilterForm(FlaskForm):
    """Форма фильтрации остатков"""
    product_id = SelectField('Товар', coerce=int, validators=[Optional()], choices=[])
    cell_id = SelectField('Ячейка', coerce=int, validators=[Optional()], choices=[])
    min_quantity = FloatField('Мин. количество', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Применить фильтр')


class FreeRoomSearchForm(FlaskForm):
    """Форма поиска свободных аудиторий (из второй курсовой, но пригодится)"""
    date = DateField('Дата', default=date.today, validators=[DataRequired()])
    start_time = StringField('Время начала (ЧЧ:ММ)', validators=[DataRequired()])
    end_time = StringField('Время окончания (ЧЧ:ММ)', validators=[DataRequired()])
    min_capacity = IntegerField('Мин. вместимость', validators=[Optional(), NumberRange(min=1)])
    has_projector = BooleanField('Проектор')
    has_computers = BooleanField('Компьютеры')
    building = StringField('Корпус', validators=[Optional(), Length(max=10)])
    submit = SubmitField('Найти')