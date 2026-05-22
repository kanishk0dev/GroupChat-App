from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO, join_room, send
import uuid
import os

app = Flask(__name__)

# ---------------- SECRET KEY ----------------

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "secret123"
)

# ---------------- SOCKET ----------------

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

# ---------------- INVITE STORAGE ----------------

invite_links = {}

# ---------------- HOME ----------------

@app.route('/')
def home():

    return render_template('login.html')

# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    username = request.form['username']

    session['username'] = username

    # invite redirect flow
    if 'invite_room' in session:

        room = session['invite_room']

        session.pop('invite_room', None)

        return redirect(f'/chat/{room}')

    return redirect('/dashboard')

# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():

    if 'username' not in session:

        return redirect('/')

    return render_template(
        'dashboard.html',
        username=session['username']
    )

# ---------------- CHAT ----------------

@app.route('/chat/<room>')
def chat(room):

    if 'username' not in session:

        return redirect('/')

    return render_template(
        'chat.html',
        username=session['username'],
        room=room
    )

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

# ---------------- GENERATE INVITE ----------------

@app.route('/generate-invite', methods=['POST'])
def generate_invite():

    room = request.form['room']

    # generate token
    token = str(uuid.uuid4())

    # store invite
    invite_links[token] = {

        "room": room,
        "used": False
    }

    BASE_URL = request.host_url.rstrip('/')

    invite_link = f"{BASE_URL}/invite/{token}"

    return jsonify({

        "link": invite_link
    })

# ---------------- INVITE ROUTE ----------------

@app.route('/invite/<token>')
def invite(token):

    # invalid token
    if token not in invite_links:

        return "Invalid Invite Link"

    # already used
    if invite_links[token]["used"]:

        return "Invite Link Expired"

    # expire after first use
    invite_links[token]["used"] = True

    room = invite_links[token]["room"]

    # save room temporarily
    session['invite_room'] = room

    # redirect login
    return redirect('/')

# ---------------- EMBED ----------------

@app.route('/embed')
def embed():

    return render_template('embed.html')

# ---------------- SOCKET JOIN ----------------

@socketio.on('join')
def handle_join(data):

    join_room(data['room'])

# ---------------- REALTIME MESSAGE ----------------

@socketio.on('message')
def handle_message(data):

    send(data, to=data['room'])

# ---------------- MAIN ----------------

if __name__ == '__main__':

    port = int(
        os.environ.get("PORT", 5000)
    )

    socketio.run(

        app,

        host='0.0.0.0',

        port=port
    )