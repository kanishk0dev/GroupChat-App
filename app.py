from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, join_room, send
import uuid
import os
import resend

app = Flask(__name__)

# ---------------- SECRET KEY ----------------

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "secret123"
)

# ---------------- RESEND CONFIG ----------------

resend.api_key = os.environ.get(
    "RESEND_API_KEY"
)

# ---------------- SOCKET ----------------

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

# ---------------- INVITES ----------------

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

    # generate unique token
    token = str(uuid.uuid4())

    # store invite
    invite_links[token] = {

        "room": room,
        "used": False
    }

    # production url
    BASE_URL = request.host_url.rstrip('/')

    invite_link = f"{BASE_URL}/invite/{token}"

    try:

        params = {

            "from":
            "Chat App <onboarding@resend.dev>",

            "to":
            [email],

            "subject":
            "Chat Room Invitation",

            "html":
            f"""
            <div style="
                font-family:Arial;
                padding:20px;
            ">

                <h2>
                    You are invited!
                </h2>

                <p>
                    Click below to join the chat room:
                </p>

                <a href="{invite_link}"
                   style="
                        display:inline-block;
                        padding:12px 20px;
                        background:#2563eb;
                        color:white;
                        text-decoration:none;
                        border-radius:10px;
                   ">
                    Join Chat Room
                </a>

                <br><br>

                <p>
                    This invite link works
                    only one time.
                </p>

            </div>
            """
        }

        resend.Emails.send(params)

        return "Invite Sent Successfully!"

    except Exception as e:

        print(e)

        return "Failed To Send Invite"

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

    # save room in session
    session['invite_room'] = room

    # redirect login
    return redirect('/')

# ---------------- EMBED ----------------

@app.route('/embed')
def embed():

    return render_template('embed.html')

# ---------------- SOCKET EVENTS ----------------

@socketio.on('join')
def handle_join(data):

    join_room(data['room'])

# realtime messages
@socketio.on('message')
def handle_message(data):

    send(data, to=data['room'])

# ---------------- MAIN ----------------

if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host='0.0.0.0',
        port=port
    )