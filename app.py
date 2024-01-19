from flask import Flask, render_template, redirect,flash,session, g
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.exceptions import Unauthorized
from models import connect_db, db
from forms import LoginForm



app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///capstone_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

app.app_context().push()
connect_db(app)


toolbar = DebugToolbarExtension(app)

@app.route("/")
def home():
  """redirect to register page"""

  return redirect("/register")


@app.route("/register")
def register():
  """register page"""
  form = LoginForm()

  return render_template("base.html", form=form)