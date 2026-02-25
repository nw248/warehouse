import pytest
from flask import session
from app import db
from app.models import User

def test_login_page(client):
    """Тест страницы входа"""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert 'Вход'.encode('utf-8') in response.data

def test_login_success(client, auth):
    """Тест успешного входа"""
    response = auth.login('admin', 'admin123')
    assert response.status_code == 200
    # Проверяем, что нет сообщения об ошибке
    assert 'Неверное имя'.encode('utf-8') not in response.data

def test_login_invalid_password(client, auth):
    """Тест входа с неверным паролем"""
    response = auth.login('admin', 'wrongpassword')
    assert response.status_code == 200
    assert 'Неверное имя'.encode('utf-8') in response.data

def test_login_invalid_username(client, auth):
    """Тест входа с неверным логином"""
    response = auth.login('nonexistent', 'admin123')
    assert response.status_code == 200
    assert 'Неверное имя'.encode('utf-8') in response.data

def test_login_empty_fields(client, auth):
    """Тест входа с пустыми полями"""
    response = auth.login('', '')
    assert response.status_code == 200
    # Должна быть ошибка валидации

def test_logout(client, auth):
    """Тест выхода из системы"""
    auth.login()
    response = auth.logout()
    assert response.status_code == 200
    # После выхода должны быть на странице входа
    assert 'Вход'.encode('utf-8') in response.data

def test_profile_page(client, auth):
    """Тест страницы профиля"""
    auth.login()
    response = client.get('/auth/profile')
    assert response.status_code == 200
    assert 'Профиль'.encode('utf-8') in response.data

def test_profile_page_without_login(client):
    """Тест доступа к профилю без авторизации"""
    response = client.get('/auth/profile')
    assert response.status_code == 302  # Должно перенаправить на логин

def test_users_list_page_admin(client, auth):
    """Тест страницы списка пользователей для админа"""
    auth.login()
    response = client.get('/auth/users')
    assert response.status_code == 200
    assert 'Пользователи'.encode('utf-8') in response.data

def test_users_list_page_non_admin(client, auth, app):
    """Тест страницы списка пользователей для не-админа"""
    # Создаем пользователя не-админа с уникальным email
    with app.app_context():
        # Проверяем, нет ли уже такого пользователя
        existing = User.query.filter_by(username='testmanager_unique').first()
        if not existing:
            user = User(
                username='testmanager_unique',
                email='manager_unique@test.com',  # Уникальный email
                full_name='Test Manager',
                role='manager'
            )
            user.set_password('manager123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        else:
            user_id = existing.id
    
    # Логинимся как менеджер
    auth.login('testmanager_unique', 'manager123')
    
    response = client.get('/auth/users')
    assert response.status_code == 302  # Должно перенаправить

def test_user_create_page_admin(client, auth):
    """Тест страницы создания пользователя для админа"""
    auth.login()
    response = client.get('/auth/users/create')
    assert response.status_code == 200
    assert 'Новый пользователь'.encode('utf-8') in response.data

def test_user_create_post_admin(client, auth, app):
    """Тест создания пользователя через POST"""
    auth.login()
    
    response = client.post('/auth/users/create', data={
        'username': 'newuser123',
        'email': 'newuser123@test.com',  # Уникальный email
        'full_name': 'New User',
        'role': 'manager',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'успешно'.encode('utf-8') in response.data
    
    with app.app_context():
        user = User.query.filter_by(username='newuser123').first()
        assert user is not None
        assert user.email == 'newuser123@test.com'
        assert user.role == 'manager'

def test_user_create_duplicate_username(client, auth, app):
    """Тест создания пользователя с существующим именем"""
    auth.login()
    
    response = client.post('/auth/users/create', data={
        'username': 'admin',  # Уже существует
        'email': 'unique_email@test.com',  # Уникальный email
        'full_name': 'New User',
        'role': 'manager',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'уже существует'.encode('utf-8') in response.data

def test_user_create_password_mismatch(client, auth):
    """Тест создания пользователя с несовпадающими паролями"""
    auth.login()
    
    response = client.post('/auth/users/create', data={
        'username': 'newuser2',
        'email': 'newuser2@test.com',
        'full_name': 'New User',
        'role': 'manager',
        'password': 'password123',
        'password2': 'different'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'пароль'.encode('utf-8') in response.data.lower()

def test_user_edit_page_admin(client, auth, app):
    """Тест страницы редактирования пользователя"""
    auth.login()
    
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        response = client.get(f'/auth/users/{user.id}/edit')
        assert response.status_code == 200
        assert 'Редактирование'.encode('utf-8') in response.data

def test_user_edit_post_admin(client, auth, app):
    """Тест редактирования пользователя"""
    auth.login()
    
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        
        response = client.post(f'/auth/users/{user.id}/edit', data={
            'username': 'admin_updated',
            'email': 'admin_updated@test.com',
            'full_name': 'Updated Admin',
            'role': 'admin'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'обновлен'.encode('utf-8') in response.data
        
        updated_user = db.session.get(User, user.id)
        assert updated_user.username == 'admin_updated'
        assert updated_user.email == 'admin_updated@test.com'

def test_user_edit_change_password(client, auth, app):
    """Тест смены пароля при редактировании"""
    auth.login()
    
    with app.app_context():
        # Создаем тестового пользователя
        test_user = User(
            username='password_test',
            email='password_test@test.com',
            full_name='Password Test',
            role='manager'
        )
        test_user.set_password('oldpassword')
        db.session.add(test_user)
        db.session.commit()
        user_id = test_user.id
    
    response = client.post(f'/auth/users/{user_id}/edit', data={
        'username': 'password_test',
        'email': 'password_test@test.com',
        'full_name': 'Password Test',
        'role': 'manager',
        'password': 'newpassword123',
        'password2': 'newpassword123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'обновлен'.encode('utf-8') in response.data
    
    with app.app_context():
        # Проверяем, что пароль изменился
        updated_user = db.session.get(User, user_id)
        assert updated_user.check_password('newpassword123') is True

def test_user_delete_admin(client, auth, app):
    """Тест удаления пользователя"""
    auth.login()
    
    with app.app_context():
        # Создаем пользователя для удаления с уникальным email
        user = User(
            username='todelete123',
            email='todelete123@test.com',
            full_name='To Delete',
            role='manager'
        )
        user.set_password('delete123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    response = client.post(f'/auth/users/{user_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'удален'.encode('utf-8') in response.data
    
    with app.app_context():
        deleted_user = db.session.get(User, user_id)
        assert deleted_user is None

def test_user_delete_self(client, auth, app):
    """Тест попытки удалить самого себя"""
    auth.login()
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        
        response = client.post(f'/auth/users/{admin.id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert 'Нельзя удалить самого себя'.encode('utf-8') in response.data
        
        # Проверяем, что админ не удалился
        admin_still_exists = db.session.get(User, admin.id)
        assert admin_still_exists is not None

def test_user_delete_non_admin(client, auth, app):
    """Тест удаления пользователя не-админом"""
    # Создаем менеджера с уникальным email
    with app.app_context():
        manager = User(
            username='testmanager456',
            email='manager456@test.com',
            full_name='Test Manager',
            role='manager'
        )
        manager.set_password('manager123')
        db.session.add(manager)
        db.session.commit()
        manager_id = manager.id
    
    # Логинимся как менеджер
    auth.login('testmanager456', 'manager123')
    
    response = client.post(f'/auth/users/{manager_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'Доступ запрещен'.encode('utf-8') in response.data