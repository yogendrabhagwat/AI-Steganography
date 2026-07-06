import re
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from extensions import db, bcrypt
from models.db_models import User


def _valid_email_or_mobile(value: str) -> bool:
    email_re = '^[\\w\\.\\+\\-]+@[\\w\\-]+\\.[a-zA-Z]{2,}$'
    mobile_re = '^\\+?[0-9]{7,15}$'
    return bool(re.match(email_re, value) or re.match(mobile_re, value))


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email_or_mobile = request.form.get('email_or_mobile', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
        elif not _valid_email_or_mobile(email_or_mobile):
            flash('Enter a valid email or mobile number.', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
        elif not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password) or not re.search(r'[\W_]', password):
            flash('Password must contain at least 1 uppercase, 1 lowercase, 1 number, and 1 special character.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
        elif User.query.filter_by(email_or_mobile=email_or_mobile).first():
            flash('Email/Mobile already registered.', 'error')
        else:
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username,
                        email_or_mobile=email_or_mobile, password_hash=hashed)
            db.session.add(user)
            db.session.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = User.query.filter((User.email_or_mobile == identifier) | (
            User.username == identifier)).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))
