from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.forms import LoginForm, UserForm
from urllib.parse import urlparse

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            flash('Вы успешно вошли в систему', 'success')
            return redirect(next_page)
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('auth/login.html', title='Вход', form=form)


@bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    return render_template('auth/profile.html', title='Профиль', user=current_user)


@bp.route('/users')
@login_required
def user_list():
    """Список пользователей (только для админа)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('auth/users.html', title='Пользователи', users=users)


@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def user_create():
    """Создание нового пользователя (только для админа)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    form = UserForm()
    if form.validate_on_submit():
        # Проверка уникальности username и email
        if User.query.filter_by(username=form.username.data).first():
            flash('Пользователь с таким именем уже существует', 'danger')
            return render_template('auth/user_form.html', title='Новый пользователь', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('auth/user_form.html', title='Новый пользователь', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Пользователь {user.username} успешно создан', 'success')
        return redirect(url_for('auth.user_list'))
    
    return render_template('auth/user_form.html', title='Новый пользователь', form=form)


@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(id):
    """Редактирование пользователя (только для админа)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    # Убираем обязательность пароля при редактировании
    form.password.validators = []
    form.password2.validators = []
    
    if form.validate_on_submit():
        # Проверка уникальности (исключая текущего пользователя)
        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username and existing_username.id != id:
            flash('Пользователь с таким именем уже существует', 'danger')
            return render_template('auth/user_form.html', title='Редактирование', form=form, user=user)
        
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email and existing_email.id != id:
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('auth/user_form.html', title='Редактирование', form=form, user=user)
        
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.role = form.role.data
        
        # Если пароль был введен - меняем
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        flash('Пользователь успешно обновлен', 'success')
        return redirect(url_for('auth.user_list'))
    
    return render_template('auth/user_form.html', title='Редактирование', form=form, user=user)


@bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def user_delete(id):
    """Удаление пользователя (только для админа)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    
    # Запрещаем удалять самого себя
    if user.id == current_user.id:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('auth.user_list'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Пользователь {user.username} удален', 'success')
    return redirect(url_for('auth.user_list'))