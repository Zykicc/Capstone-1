from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.exceptions import Unauthorized
from sqlalchemy.exc import IntegrityError
from models import connect_db, db, User
from forms import LoginForm, SignUpForm, GetUser1, GetUser2
import requests
import re

CURR_USER_KEY = "curr_user"


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///capstone_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

app.app_context().push()
connect_db(app)


toolbar = DebugToolbarExtension(app)

authToken = ""

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]




@app.route("/register", methods=["GET", "POST"])
def signup():
  """register page"""


  form = SignUpForm()

  if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('signup_page.html', form=form)

        do_login(user)

        return redirect("/")

  return render_template("signup_page.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
  """Login page"""

  form = LoginForm()

  if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')
  

  return render_template("Login_page.html", form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()
    flash("Goodbye!", "info")
    return redirect('/')


@app.route('/getUserPlaylists', methods=["GET", "POST"])
def getUserPlaylists():
    """Gets all user playlists"""

    print("#################################################")

    if 'user1_id' in request.form:
        user_id = request.form['user1_id']
    else:
        user_id = request.form['user2_id']

    # user_id = request.form['user1_id'];

    authToken = getToken()

    userId = re.search(r'(?<=open\.spotify\.com/user/)(.*)(?=\?si=)', user_id).group()

    url = f"https://api.spotify.com/v1/users/{userId}/playlists"
    headers = {
    'Authorization': f"Bearer {authToken}"
    }
    playlist = requests.request("GET", url, headers=headers)
    print("#################################################")

    new_playlist = []
    for item in playlist.json()["items"]:
        new_playlist.append({ 
            'name': item["name"], 
            'id': item["id"],
            'image': item["images"][0]["url"] 
        })
        # print(item["name"])
    # print(playlist.json()["items"][0]["name"])
    print(new_playlist)
    # session["user1_playlist"] = new_playlist

    if 'user1_id' in request.form:
        session["user1_playlist"] = new_playlist
    else:
        session["user2_playlist"] = new_playlist
 
    
    
    
    return redirect('/')

##############################TOKEN###################################
def getToken():
    url = "https://accounts.spotify.com/api/token"

    payload = 'grant_type=client_credentials&client_id=32dcf2a655a84387beb033858c58c4fa&client_secret=8c2e1661ebbf48d4978fed7bc585ee23'
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': '__Host-device_id=AQD0pt6oHOfQGGyBUbX5sfdR9EX3CCEKg9DhURAZOYdWezEn68ssw0XnELO0LI7HcGIZBOpZMhcSjnbAkUcJyLtWNpm5PJackds'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json().get("access_token")

# #####################################################################

@app.route("/", methods=["GET", "POST"])
def home_page():
    """home page"""
    
    form1 = GetUser1()
    form2 = GetUser2()
    print("############################################")
    playListUser1 = []
    playListUser2 = []
    if 'user1_playlist' in session:
        playListUser1 = session["user1_playlist"]
        print(session["user1_playlist"])

    if 'user2_playlist' in session:
        playListUser2 = session["user2_playlist"]
        print(session["user2_playlist"])
    print("############################################")

#   if form1.validate_on_submit():
#     authToken = getToken()
#     user1_id = form1.user_id.data

#     userId = re.search(r'(?<=open\.spotify\.com/user/)(.*)(?=\?si=)', user1_id).group()

#     url = f"https://api.spotify.com/v1/users/{userId}/playlists"
#     headers = {
#     'Authorization': f"Bearer {authToken}"
#     }
#     playlist = requests.request("GET", url, headers=headers)
#     print("#################################################")
#     print(playlist.json().get("items")) 

#   if form2.validate_on_submit():
#     user1_id = form2.user_id.data
#     url = f"https://api.spotify.com/v1/users/{user1_id}/playlists"

        


    if g.user:
        return render_template('home.html', form1=form1, form2=form2, playListUser1=playListUser1, playListUser2=playListUser2)
  
    else:
        return render_template("home_anon.html")
