import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from models import User, Organization
from app import db

auth_bp = Blueprint('auth', __name__)

# Define forms for authentication
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    organization_name = StringField('Organization Name', validators=[DataRequired(), Length(max=128)])
    is_msp = BooleanField('This is an MSP organization')
    terms = BooleanField('I agree to the Terms and Conditions', validators=[DataRequired()])

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    
class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            user.update_last_login()
            db.session.commit()
            
            # Store user preferences in session
            session['theme'] = user.get_preferences().get('theme', 'dark')
            
            # Record login session
            record_login_session(user)
            
            # Get next page or default to dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'error')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'error')
            return render_template('register.html', form=form)
        
        # Create organization
        organization = Organization(
            name=form.organization_name.data,
            is_msp=form.is_msp.data
        )
        db.session.add(organization)
        db.session.flush()  # Flush to get organization id
        
        # Create user with admin privileges
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=True,
            preferences='{"theme": "dark"}'
        )
        user.set_password(form.password.data)
        
        # Add user to organization
        user.organizations.append(organization)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate password reset token
            token = user.generate_reset_token()
            
            # In a production environment, you would send an email with the reset link
            # For this implementation, we'll just flash the token
            flash(f'Password reset link has been sent to your email: {form.email.data}', 'info')
            
            # Redirect to prevent form resubmission
            return redirect(url_for('auth.login'))
        else:
            flash('Email not found', 'error')
    
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Verify the token and get user
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form)

@auth_bp.route('/terms')
def terms():
    return render_template('terms.html')

def record_login_session(user):
    """Record user login session with IP address and device info"""
    try:
        from models import UserSession
        import datetime
        
        # Get client information
        ip_address = request.remote_addr
        user_agent = request.user_agent.string
        device_type = 'Unknown'
        
        # Detect device type from user agent
        if 'Mobile' in user_agent:
            device_type = 'Mobile'
        elif 'Tablet' in user_agent:
            device_type = 'Tablet'
        else:
            device_type = 'Desktop'
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            last_active=datetime.datetime.utcnow()
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Store session ID
        session['session_id'] = session.id
    except Exception as e:
        # Log error but don't prevent login
        print(f"Error recording login session: {e}")
