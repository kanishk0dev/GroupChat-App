from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, join_room, send
import uuid
import os
import requests

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

# ---------------- INVITES STORAGE ----------------

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

# ---------------- SEND INVITE ----------------

@app.route('/send-invite', methods=['POST'])
def send_invite():

    try:

        email = request.form['email']

        room = request.form['room']

        # generate token
        token = str(uuid.uuid4())

        # save invite
        invite_links[token] = {

            "room": room,
            "used": False
        }

        # base url
        BASE_URL = request.host_url.rstrip('/')

        # invite link
        invite_link = f"{BASE_URL}/invite/{token}"

        # api key
        api_key = os.environ.get(
            "RESEND_API_KEY"
        )

        print("API KEY:", api_key)

        # request headers
        headers = {

            "Authorization":
            f"Bearer {api_key}",

            "Content-Type":
            "application/json"
        }

        # email data
        data = {

            "from":
            "onboarding@resend.dev",

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
                    You are Invited!
                </h2>

                <p>
                    Click below to join the chat room:
                </p>

                <a href="{invite_link}"
                   style="
                        background:#2563eb;
                        color:white;
                        padding:12px 20px;
                        border-radius:10px;
                        text-decoration:none;
                        display:inline-block;
                   ">
                    Join Chat Room
                </a>

                <br><br>

                <b>
                    This invite link works
                    only one time.
                </b>

            </div>
            """
        }

        # resend request
        response = requests.post(

            "https://api.resend.com/emails",

            headers=headers,

            json=data
        )

        print("STATUS CODE:", response.status_code)

        print("RESPONSE:", response.text)

        # success
        if response.status_code in [200, 201]:

            return "Invite Sent Successfully!"

        # failed
        else:

            return f"ERROR: {response.text}"

    except Exception as e:

        print("EXCEPTION:", e)

        return f"EXCEPTION: {str(e)}"

# ---------------- INVITE ROUTE ----------------

@app.route('/invite/<token>')
def invite(token):

    # invalid token
    if token not in invite_links:

        return "Invalid Invite Link"

    # already used
    if invite_links[token]["used"]:

        return "Invite Link Expired"

    # expire after first click
    invite_links[token]["used"] = True

    room = invite_links[token]["room"]

    # temporary session storage
    session['invite_room'] = room

    # redirect to login
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