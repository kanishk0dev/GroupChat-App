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

    try:

        email = request.form['email']

        room = request.form['room']

        # generate unique token
        token = str(uuid.uuid4())

        # save invite
        invite_links[token] = {

            "room": room,
            "used": False
        }

        BASE_URL = request.host_url.rstrip('/')

        invite_link = f"{BASE_URL}/invite/{token}"

        # ---------------- RESEND API ----------------

        api_key = os.environ.get(
            "RESEND_API_KEY"
        )

        headers = {

            "Authorization":
            f"Bearer {api_key}",

            "Content-Type":
            "application/json"
        }

        data = {

            "from":
            "Chat App <onboarding@resend.dev>",

            "to":
            [email],

            "subject":
            "Chat Room Invitation",

            "html":
            f"""
            <div style='font-family:Arial;'>

                <h2>
                    Chat Room Invite
                </h2>

                <p>
                    Click below to join:
                </p>

                <a href="{invite_link}"
                   style="
                        background:#2563eb;
                        color:white;
                        padding:12px 20px;
                        text-decoration:none;
                        border-radius:10px;
                        display:inline-block;
                   ">
                    Join Chat
                </a>

                <br><br>

                <b>
                    This invite works only once.
                </b>

            </div>
            """
        }

        response = requests.post(

            "https://api.resend.com/emails",

            headers=headers,

            json=data
        )

        print(response.text)

        if response.status_code == 200:

            return "Invite Sent Successfully!"

        else:

            return "Failed To Send Invite"

    except Exception as e:

        print(e)

        return "Error Sending Invite"

# ---------------- INVITE ----------------

@app.route('/invite/<token>')
def invite(token):

    # invalid link
    if token not in invite_links:

        return "Invalid Invite Link"

    # already used
    if invite_links[token]["used"]:

        return "Invite Link Expired"

    # expire link
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

# ---------------- SOCKET ----------------

@socketio.on('join')
def handle_join(data):

    join_room(data['room'])

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