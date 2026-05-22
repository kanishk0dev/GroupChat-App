from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import uuid
import os

app = Flask(__name__)

# ---------------- IFRAME SUPPORT ----------------

@app.after_request
def add_header(response):

    response.headers['X-Frame-Options'] = 'ALLOWALL'

    response.headers['Content-Security-Policy'] = "frame-ancestors *"

    return response

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

# ---------------- STORAGE ----------------

invite_links = {}

room_admins = {}

room_users = {}

connected_users = {}

# ---------------- HOME ----------------

@app.route('/')
def home():

    return render_template('login.html')

# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    username = request.form['username']

    # hidden unique id
    session['user_id'] = str(uuid.uuid4())

    session['username'] = username

    # invite flow
    if 'invite_room' in session:

        room = session['invite_room']

        session.pop('invite_room', None)

        session['is_invited_user'] = True

        return redirect(f'/chat/{room}')

    session['is_invited_user'] = False

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

    username = session['username']

    # first user becomes admin
    if room not in room_admins:

        room_admins[room] = username

    is_admin = room_admins[room] == username

    # invited users cannot invite
    if session.get('is_invited_user'):

        is_admin = False

    return render_template(

        'chat.html',

        username=username,

        room=room,

        is_admin=is_admin
    )

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

# ---------------- GENERATE INVITE ----------------

@app.route('/generate-invite', methods=['POST'])
def generate_invite():

    # invited users blocked
    if session.get('is_invited_user'):

        return jsonify({

            "error":
            "Not Allowed"
        })

    room = request.form['room']

    token = str(uuid.uuid4())

    invite_links[token] = {

        "room": room,
        "used": False
    }

    BASE_URL = request.host_url.rstrip('/')

    invite_link = f"{BASE_URL}/invite/{token}"

    return jsonify({

        "link": invite_link
    })

# ---------------- INVITE ----------------

@app.route('/invite/<token>')
def invite(token):

    if token not in invite_links:

        return "Invalid Invite Link"

    if invite_links[token]["used"]:

        return "Invite Link Expired"

    # one time use
    invite_links[token]["used"] = True

    room = invite_links[token]["room"]

    session['invite_room'] = room

    return redirect('/')

# ---------------- EMBED ----------------

@app.route('/embed')
def embed():

    return render_template('embed.html')

# ---------------- UPDATE USERS ----------------

def update_room_users(room):

    if room not in room_users:

        room_users[room] = []

    users_list = []

    for user in room_users[room]:

        users_list.append({

            "username": user['username'],

            "admin":
            user['username'] == room_admins.get(room)
        })

    socketio.emit(

        'update_users',

        {

            "count": len(room_users[room]),

            "users": users_list
        },

        room=room
    )

# ---------------- JOIN ----------------

@socketio.on('join')
def handle_join(data):

    room = data['room']

    username = data['username']

    user_id = data['user_id']

    join_room(room)

    connected_users[request.sid] = {

        "username": username,

        "room": room,

        "user_id": user_id
    }

    if room not in room_users:

        room_users[room] = []

    # unique by user_id
    user_exists = False

    for user in room_users[room]:

        if user['user_id'] == user_id:

            user_exists = True

    if not user_exists:

        room_users[room].append({

            "user_id": user_id,

            "username": username
        })

        # joined message

        emit(

            'user_status',

            {

                "message":
                f"{username} joined the chat"
            },

            room=room
        )

    update_room_users(room)

# ---------------- MESSAGE ----------------

@socketio.on('message')
def handle_message(data):

    emit(

        'message',

        data,

        room=data['room']
    )

# ---------------- DELETE MESSAGE ----------------

@socketio.on('delete_message')
def delete_message(data):

    emit(

        'delete_message',

        {

            "id": data['id']

        },

        room=data['room']
    )

# ---------------- DISCONNECT ----------------

@socketio.on('disconnect')
def disconnect_user():

    if request.sid not in connected_users:

        return

    user_data = connected_users[request.sid]

    room = user_data['room']

    user_id = user_data['user_id']

    username = user_data['username']

    leave_room(room)

    if room in room_users:

        room_users[room] = [

            user for user in room_users[room]

            if user['user_id'] != user_id
        ]

    # left message

    emit(

        'user_status',

        {

            "message":
            f"{username} left the chat"
        },

        room=room
    )

    update_room_users(room)

    del connected_users[request.sid]

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