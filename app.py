from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.exceptions import Unauthorized
from sqlalchemy.exc import IntegrityError
from models import connect_db, db, User
from forms import LoginForm, SignUpForm, GetUser1, GetUser2
import requests
import re
import pickle

# keys
USER1_PLAYLIST = "user1_playlist"
USER2_PLAYLIST = "user2_playlist"

USER1_SONGLIST = "user1_songlist"
USER2_SONGLIST = "user2_songlist"

USER1_SELECTED_PLAYLIST_ID = "USER1_SELECTED_PLAYLIST_ID" 
USER2_SELECTED_PLAYLIST_ID = "USER2_SELECTED_PLAYLIST_ID"

CHEMISTRY_DATA = "CHEMISTRY_DATA"

CURR_USER_KEY = "curr_user"


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///capstone_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)

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


################################################################################


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

################################################################################

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

################################################################################


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()
    flash("Goodbye!", "info")
    return redirect('/')

################################################################################


@app.route('/getUserPlaylists', methods=["GET", "POST"])
def getUserPlaylists():
    """Gets all user playlists"""

    # print("#################################################")

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
            'image': item["images"][0]["url"],
            'songCount': item["tracks"]["total"]
        })

    if 'user1_id' in request.form:
        writeDataToPickle(USER1_PLAYLIST, new_playlist)
    else:
        writeDataToPickle(USER2_PLAYLIST, new_playlist)
    
    return redirect('/')

################################################################################

def get1000songs(playlistId, songCount):
    authToken = getToken()

    collectedSongs = []
    offsets = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
    for offset in offsets:
        url = f"https://api.spotify.com/v1/playlists/{playlistId}/tracks?offset={offset}&limit=100"
        headers = {
        'Authorization': f"Bearer {authToken}"
        }
        songList = requests.request("GET", url, headers=headers)
        collectedSongs.extend(songList.json()["items"])
        if len(collectedSongs) >= songCount:
            break;
    return collectedSongs

@app.route("/getPlaylistItems/<string:userId>/<string:playlistId>", methods=["GET"])
def getPlaylistItems(userId, playlistId):
    """gets all songs in the playlist"""

    # authToken = getToken()

    # url = f"https://api.spotify.com/v1/playlists/{playlistId}/tracks?offset=0&limit=100"
    # headers = {
    # 'Authorization': f"Bearer {authToken}"
    # }
    # songList = requests.request("GET", url, headers=headers)
    if userId == "user1":
        playListUser = getDataFromPickle(USER1_PLAYLIST)
    else:
        playListUser = getDataFromPickle(USER2_PLAYLIST)
    selectedPlayList = [playlist for playlist in playListUser if playlist["id"] == playlistId]
    selectedPlayList = selectedPlayList[0]

    songList = get1000songs(playlistId, selectedPlayList["songCount"])

    new_songList = []
    for item in songList:
        if(item["track"] is not None):
            artistList = []
            artistIdList = []
            for artist in item["track"]["artists"]:
                artistIdList.append(artist["id"])
                artistList.append(artist["name"])

            new_songList.append({ 
                'name': item["track"]["name"], 
                'id': item["track"]["id"],
                'artists': artistList,
                'artistIds': artistIdList,
                'album': item["track"]["album"]["name"],
                'albumIds': item["track"]["album"]["id"]
            })
        else:
            print("**************************************************")
            print(item)

    
    if userId == "user1":
        writeDataToPickle(USER1_SONGLIST, new_songList)
        session[USER1_SELECTED_PLAYLIST_ID] = playlistId
    else:
        writeDataToPickle(USER2_SONGLIST, new_songList)
        session[USER2_SELECTED_PLAYLIST_ID] = playlistId
    



    return redirect("/")



@app.route("/compareUsersPlaylists", methods=["GET", "POST"])
def comparePlaylists():
    """Gathers users playlists data and compares them"""

    songListUser1 = getDataFromPickle(USER1_SONGLIST)
    songListUser2 = getDataFromPickle(USER2_SONGLIST)

    nameList1 = []
    idList1 = []
    artistList1 = []
    albumList1 = []


    for song in songListUser1:
        # nameList1.append(song["name"])
        idList1.append(song["id"])
        albumList1.append(song["albumIds"])

        for artist in song["artistIds"]:
            artistList1.append(artist)

    artistList1 = list(set(artistList1))  
    idList1 = list(set(idList1))
    albumList1 = list(set(albumList1))
        

    nameList2 = []
    idList2 = []
    artistList2 = []
    albumList2 = []


    for song in songListUser2:
        # nameList2.append(song["name"])
        idList2.append(song["id"])
        albumList2.append(song["albumIds"])

        for artist in song["artistIds"]:
            artistList2.append(artist)

    artistList2 = list(set(artistList2))  
    idList2 = list(set(idList2))
    albumList2 = list(set(albumList2))

    sameSongCount = len(list(set(idList1).intersection(idList2)))
    sameArtistCount = len(list(set(artistList1).intersection(artistList2)))
    sameAlbumCount = len(list(set(albumList1).intersection(albumList2)))

    print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
    print(sameSongCount)
    print(sameArtistCount)
    print(sameAlbumCount)
    
    
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    toalSongs = []
    toalSongs.extend(idList1)
    toalSongs.extend(idList2)
    totalSongCount = len(list(set(toalSongs)))

    toalartists = []
    toalartists.extend(artistList1)
    toalartists.extend(artistList2)
    totalArtistCount = len(list(set(toalartists)))

    toalAlbums = []
    toalAlbums.extend(albumList1)
    toalAlbums.extend(albumList2)
    totalAlbumCount = len(list(set(toalAlbums)))

    spotifyChemPerc = format((sameSongCount + sameArtistCount + sameAlbumCount) / (totalSongCount + totalArtistCount + totalAlbumCount), ".0%")
    print(spotifyChemPerc)
    
    chemData = {
        'sameSongCount': sameSongCount,
        'sameArtistCount': sameArtistCount,
        'sameAlbumCount': sameAlbumCount,
        'spotifyChemPerc': spotifyChemPerc
    }

    session[CHEMISTRY_DATA] = chemData

    return redirect("/")






########################################################################
@app.route('/clearData', methods=["GET"])
def clearData():
    """Handle logout of user."""
    writeDataToPickle(USER1_PLAYLIST, [])
    writeDataToPickle(USER2_PLAYLIST, [])

    writeDataToPickle(USER1_SONGLIST, [])
    writeDataToPickle(USER2_SONGLIST, [])


    if USER1_SELECTED_PLAYLIST_ID in session:
        del session[USER1_SELECTED_PLAYLIST_ID]
    
    if USER2_SELECTED_PLAYLIST_ID in session:
        del session[USER2_SELECTED_PLAYLIST_ID]
    
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

######################################################################

def writeDataToPickle(fileName, data):
    if len(data) == 0:
        open(f'{fileName}.pickle', "w").close()
    else:
        with open(f'{fileName}.pickle', "wb") as file:
                pickle.dump(data, file)

def getDataFromPickle(fileName):
    data = []
    try:
        with (open(f'{fileName}.pickle', "rb")) as openfile:
            while True:
                try:
                    data = pickle.load(openfile)
                except EOFError:
                    break
    except FileNotFoundError:
        return []
    return data

##################################################################
@app.route("/", methods=["GET", "POST"])
def home_page():
    """home page"""
    
    form1 = GetUser1()
    form2 = GetUser2()


    
    playListUser1 = getDataFromPickle(USER1_PLAYLIST)
    playListUser2 = getDataFromPickle(USER2_PLAYLIST)

    filledBothSongList = False
    songListUser1 = getDataFromPickle(USER1_SONGLIST)
    songListUser2 = getDataFromPickle(USER2_SONGLIST)

    # print(songListUser1)
    # print(songListUser2)

    if len(songListUser1) != 0 and len(songListUser2) != 0:
        filledBothSongList = True
    else:
        filledBothSongList = False

    selectedUser1PlaylistId = ""
    selectedUser2PlaylistId = ""

    if USER1_SELECTED_PLAYLIST_ID in session:
        selectedUser1PlaylistId = session[USER1_SELECTED_PLAYLIST_ID]
    
    if USER2_SELECTED_PLAYLIST_ID in session:
        selectedUser2PlaylistId = session[USER2_SELECTED_PLAYLIST_ID]
    

    chemistryData = {}
    if CHEMISTRY_DATA in session:
        chemistryData = session[CHEMISTRY_DATA]
    else:
        chemistryData = False
    
    # print(filledBothSongList)

    if g.user:
        return render_template('home.html', form1=form1, form2=form2, playListUser1=playListUser1, playListUser2=playListUser2, showCompareBtn=filledBothSongList, selectedUser1PlaylistId=selectedUser1PlaylistId, selectedUser2PlaylistId=selectedUser2PlaylistId, chemistryData=chemistryData)
  
    else:
        return render_template("home_anon.html")
