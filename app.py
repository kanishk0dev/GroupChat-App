from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, join_room, send
from flask_mail import Mail, Message
import uuid

app = Flask(__name__)

app.secret_key = "secret123"

# ---------------- MAIL CONFIG ----------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = 'groupchatapp1@gmail.com'

app.config['MAIL_PASSWORD'] = 'hahy kond rzjy vbpo'

mail = Mail(app)

# ---------------- SOCKET ----------------

socketio = SocketIO(app)

# ---------------- INVITES ----------------

invite_links = {}

# ---------------- HOME ----------------

@app.route('/')
def home():

    return render_template('login.html')


# ---------------- IFRAME ----------------

@app.route('/embed')
def embed():

    return render_template('embed.html')

# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    username = request.form['username']

    session['username'] = username

    # invite flow
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

# ---------------- SEND INVITE ----------------

@app.route('/send-invite', methods=['POST'])
def send_invite():

    email = request.form['email']
    room = request.form['room']

    token = str(uuid.uuid4())

    invite_links[token] = {

        "room": room,
        "used": False
    }

    invite_link = f"http://127.0.0.1:5000/invite/{token}"

    # ---------------- EMAIL ----------------

    msg = Message(

        subject="Chat Room Invitation",

        sender=app.config['MAIL_USERNAME'],

        recipients=[email]
    )

    msg.body = f"""
Hello,

You have been invited to join a chat room.

Click the link below:

{invite_link}

IMPORTANT:
This link can only be used ONE TIME.

After opening once,
it will expire automatically.
"""

    mail.send(msg)

    return "Invite Sent Successfully!"

# ---------------- INVITE ----------------

@app.route('/invite/<token>')
def invite(token):

    # invalid token
    if token not in invite_links:

        return "Invalid Invite Link"

    # already used
    if invite_links[token]["used"]:

        return "Invite Link Expired"

    # expire link after first click
    invite_links[token]["used"] = True

    room = invite_links[token]["room"]

    # save room temporarily
    session['invite_room'] = room

    # redirect to login
    return redirect('/')

# ---------------- SOCKET ----------------

@socketio.on('join')
def handle_join(data):

    join_room(data['room'])

# realtime messages
@socketio.on('message')
def handle_message(data):

    send(data, to=data['room'])

# ---------------- MAIN ----------------

if __name__ == '__main__':

    socketio.run(
        app,
        host='0.0.0.0',
        port=5000
    )