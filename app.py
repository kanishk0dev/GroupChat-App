from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, join_room, send
import uuid
import json
import urllib.request
import urllib.error

# ---------------- CONFIG ----------------

SECRET_KEY = "your_secret_key"

# Resend API Key
RESEND_API_KEY = "re_ArmW8zi2_FP4VyPXJBLZL6YX6TRogkQta"

# Your Resend Account Email
SENDER_EMAIL = "groupchatapp1@gmail.com"

# ---------------- FLASK ----------------

app = Flask(__name__)

app.secret_key = SECRET_KEY

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

# ---------------- SEND INVITE ----------------

@app.route('/send-invite', methods=['POST'])
def send_invite():

    try:

        email = request.form['email']

        room = request.form['room']

        # unique invite token
        token = str(uuid.uuid4())

        # store invite
        invite_links[token] = {

            "room": room,
            "used": False
        }

        # base url
        BASE_URL = request.host_url.rstrip('/')

        # invite link
        invite_link = f"{BASE_URL}/invite/{token}"

        # email payload
        payload = {

            # KEEP THIS FOR TESTING
            "from":
            "onboarding@resend.dev",

            "to":
            [email],

            "subject":
            "Chat Room Invitation",

            "html":
            f"""
            <div style='font-family:Arial;padding:20px;'>

                <h2>
                    You are invited!
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
                    This invite link works only once.
                </b>

            </div>
            """
        }

        # convert json
        data = json.dumps(payload).encode("utf-8")

        # api request
        req = urllib.request.Request(

            "https://api.resend.com/emails",

            data=data,

            headers={

                "Authorization":
                f"Bearer {RESEND_API_KEY}",

                "Content-Type":
                "application/json"
            },

            method="POST"
        )

        try:

            response = urllib.request.urlopen(req)

            response_data = response.read().decode()

            print("EMAIL SENT")

            print(response_data)

            return "Invite Sent Successfully!"

        except urllib.error.HTTPError as e:

            error_message = e.read().decode()

            print("HTTP ERROR:", error_message)

            return f"ERROR: {error_message}"

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

    # expire link
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

    socketio.run(

        app,

        host='0.0.0.0',

        port=5000
    )