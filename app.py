from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import uuid
import os

app = Flask(__name__)

# ---------------- SESSION CONFIG ----------------

app.config['SESSION_COOKIE_SAMESITE'] = "None"
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

# ---------------- IFRAME SUPPORT ----------------

@app.after_request
def add_header(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# ---------------- SECRET KEY ----------------

app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# ---------------- SOCKET ----------------

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=True
)

# ---------------- STORAGE ----------------

# room -> single permanent token (never expires)
room_invite_tokens = {}

# token -> room (reverse lookup)
token_to_room = {}

# room -> admin user_id
room_admins = {}

# room -> list of users
room_users = {}

# sid -> user data
connected_users = {}

# ---------------- HOME ----------------

@app.route('/')
def home():
    return render_template(
        'login.html',
        invite_room=session.get('invite_room', '')
    )

# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    username = request.form.get('username', '').strip()

    if not username:
        return redirect('/')

    session['user_id'] = str(uuid.uuid4())
    session['username'] = username

    if 'invite_room' in session:
        room = session.pop('invite_room')
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
    user_id  = session['user_id']

    # first person into the room becomes admin
    if room not in room_admins:
        room_admins[room] = user_id
        # creator is never an invited user
        session['is_invited_user'] = False

    is_admin = (room_admins[room] == user_id)

    # invited users can never invite others
    if session.get('is_invited_user'):
        is_admin = False

    return render_template(
        'chat.html',
        username=username,
        room=room,
        is_admin=is_admin
    )

# ---------------- GENERATE INVITE ----------------

@app.route('/generate-invite', methods=['POST'])
def generate_invite():

    # must be logged in
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    # invited users cannot generate links
    if session.get('is_invited_user') is True:
        return jsonify({"error": "Not allowed"}), 403

    room = request.form.get('room', '').strip()
    if not room:
        return jsonify({"error": "Room not specified"}), 400

    # FIX: only the admin of this room can generate a link
    user_id = session['user_id']
    if room in room_admins and room_admins[room] != user_id:
        return jsonify({"error": "Not the admin"}), 403

    # reuse existing token for this room, or create one
    if room not in room_invite_tokens:
        token = str(uuid.uuid4())
        room_invite_tokens[room] = token
        token_to_room[token] = room
    else:
        token = room_invite_tokens[room]

    BASE_URL = request.host_url.rstrip('/')
    invite_link = f"{BASE_URL}/invite/{token}"

    return jsonify({"link": invite_link})

# ---------------- INVITE ----------------

@app.route('/invite/<token>')
def invite(token):

    # FIX: use reverse lookup dict — O(1), no loop
    room = token_to_room.get(token)

    if not room:
        return "Invalid invite link.", 404

    session['invite_room'] = room
    return redirect('/')

# ---------------- EMBED ----------------

@app.route('/embed')
def embed():
    return render_template('embed.html')

# ---------------- UPDATE USERS ----------------

def update_room_users(room):
    users_list = [
        {
            "username": u['username'],
            "admin": u['user_id'] == room_admins.get(room)
        }
        for u in room_users.get(room, [])
    ]
    socketio.emit(
        'update_users',
        {"count": len(users_list), "users": users_list},
        room=room
    )

# ---------------- JOIN ----------------

@socketio.on('join')
def handle_join(data):
    room     = data['room']
    username = data['username']
    user_id  = data['user_id']

    join_room(room)

    connected_users[request.sid] = {
        "username": username,
        "room":     room,
        "user_id":  user_id
    }

    if room not in room_users:
        room_users[room] = []

    already_in = any(
        u['user_id'] == user_id
        for u in room_users[room]
    )

    if not already_in:
        room_users[room].append({
            "user_id":  user_id,
            "username": username
        })
        emit(
            'user_status',
            {"message": f"{username} joined the chat"},
            room=room
        )

    update_room_users(room)

# ---------------- MESSAGE ----------------

@socketio.on('message')
def handle_message(data):
    emit('message', data, room=data['room'])

# ---------------- DELETE MESSAGE ----------------

@socketio.on('delete_message')
def delete_message(data):
    emit(
        'delete_message',
        {"id": data['id']},
        room=data['room']
    )

# ---------------- DISCONNECT ----------------

@socketio.on('disconnect')
def disconnect_user():
    if request.sid not in connected_users:
        return

    user_data = connected_users.pop(request.sid)
    room      = user_data['room']
    user_id   = user_data['user_id']
    username  = user_data['username']

    leave_room(room)

    if room in room_users:
        room_users[room] = [
            u for u in room_users[room]
            if u['user_id'] != user_id
        ]

    emit(
        'user_status',
        {"message": f"{username} left the chat"},
        room=room
    )

    update_room_users(room)

# ---------------- MAIN ----------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)