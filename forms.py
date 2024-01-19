from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, Email, DataRequired



class LoginForm(FlaskForm):
  """Login form."""

  username = StringField('Enter your username', validators=[DataRequired()])
  password = PasswordField('Enter your password', validators=[Length(min=6)])
