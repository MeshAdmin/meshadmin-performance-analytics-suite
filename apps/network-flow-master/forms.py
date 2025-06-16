from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo, ValidationError
from models import User, Role

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
               'Usernames must start with a letter and can only contain '
               'letters, numbers, dots or underscores')])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(8, 128),
        EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[
        DataRequired(), Length(8, 128),
        EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm new password', validators=[DataRequired()])
    submit = SubmitField('Update Password')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('Reset Password')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(8, 128),
        EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    role = SelectField('Role', coerce=int)
    name = StringField('Full Name', validators=[Length(0, 120)])
    company = StringField('Company', validators=[Length(0, 120)])
    active = BooleanField('Active')
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]

class ForwardTargetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 128)])
    ip_address = StringField('IP Address', validators=[DataRequired(), Length(1, 45)])
    port = StringField('Port', validators=[DataRequired()])
    protocol = SelectField('Protocol', choices=[('udp', 'UDP'), ('tcp', 'TCP')])
    flow_type = SelectField('Flow Type', choices=[
        ('netflow', 'NetFlow'), 
        ('sflow', 'sFlow'),
        ('all', 'All')
    ])
    flow_version = StringField('Flow Version', validators=[Length(0, 16)])
    
    # Basic Filtering options
    filter_src_ip = StringField('Filter Source IP (CIDR)', validators=[Length(0, 45)])
    filter_dst_ip = StringField('Filter Destination IP (CIDR)', validators=[Length(0, 45)])
    filter_protocol = StringField('Filter Protocols (comma-separated)', validators=[Length(0, 64)])
    
    # Advanced Filtering options
    advanced_filtering = BooleanField('Enable Advanced Filtering')
    
    filter_src_port_min = StringField('Min Source Port', validators=[Length(0, 5)])
    filter_src_port_max = StringField('Max Source Port', validators=[Length(0, 5)])
    filter_dst_port_min = StringField('Min Destination Port', validators=[Length(0, 5)])
    filter_dst_port_max = StringField('Max Destination Port', validators=[Length(0, 5)])
    
    filter_tos = StringField('Type of Service (comma-separated)', validators=[Length(0, 32)])
    
    filter_bytes_min = StringField('Min Bytes', validators=[Length(0, 20)])
    filter_bytes_max = StringField('Max Bytes', validators=[Length(0, 20)])
    
    filter_packets_min = StringField('Min Packets', validators=[Length(0, 20)])
    filter_packets_max = StringField('Max Packets', validators=[Length(0, 20)])
    
    filter_custom_rules = TextAreaField('Custom Filter Rules (JSON)', 
                           validators=[Length(0, 4096)],
                           description='Advanced JSON-based filtering rules')
    
    # TLS options
    use_tls = BooleanField('Use TLS')
    tls_cert = StringField('TLS Certificate Path', validators=[Length(0, 512)])
    tls_key = StringField('TLS Key Path', validators=[Length(0, 512)])
    
    # Storage option
    store_locally = BooleanField('Store Copy Locally', default=True)
    
    submit = SubmitField('Save')
    
    def validate_filter_custom_rules(self, field):
        """Validate that custom rules are valid JSON if provided"""
        if field.data:
            try:
                import json
                json.loads(field.data)
            except json.JSONDecodeError:
                raise ValidationError('Custom rules must be valid JSON')