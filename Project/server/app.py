import json
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
import socketio
import uvicorn
import logging

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI()

# Socket.IO 서버 생성
sio = socketio.AsyncServer(async_mode='asgi')
socket_app = socketio.ASGIApp(sio, app)

# 사용자 데이터 파일 경로
USER_DATA_FILE = 'C://Users//luvwl//OneDrive//문서//GitHub//university//Project//data//users.json'
FRIENDS_DIR = 'C://Users//luvwl//OneDrive//문서//GitHub//university//Project//data//friends'
CHAT_HISTORY_DIR = 'C://Users//luvwl//OneDrive//문서//GitHub//university//Project//data//chat_history'

if not os.path.exists(FRIENDS_DIR):
    os.makedirs(FRIENDS_DIR)

if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic 모델 정의
class User(BaseModel):
    student_staff_number: str
    username: str
    password: str
    email: EmailStr

class LoginRequest(BaseModel):
    student_staff_number: str
    password: str

class SignupRequest(User):
    confirm_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class AddFriendRequest(BaseModel):
    student_staff_number: str
    friend_username: str

def save_user(student_staff_number, username, password, email):
    users = load_users()
    users[student_staff_number] = {
        'username': username,
        'password': password,
        'email': email
    }
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(users, file, ensure_ascii=False, indent=4)

def load_users():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

def load_friends(student_staff_number):
    friends_file = os.path.join(FRIENDS_DIR, f"{student_staff_number}.txt")
    if not os.path.exists(friends_file):
        return []
    with open(friends_file, 'r', encoding='utf-8') as file:
        return file.read().splitlines()

def save_friends(student_staff_number, friends):
    friends_file = os.path.join(FRIENDS_DIR, f"{student_staff_number}.txt")
    with open(friends_file, 'w', encoding='utf-8') as file:
        file.write("\n".join(friends))

def save_message(from_student_staff_number, to_student_staff_number, message):
    chat_file = os.path.join(CHAT_HISTORY_DIR, f"{from_student_staff_number}_to_{to_student_staff_number}.txt")
    with open(chat_file, 'a', encoding='utf-8') as file:
        file.write(f"{from_student_staff_number}: {message}\n")

def load_chat_history(from_student_staff_number, to_student_staff_number):
    chat_file = os.path.join(CHAT_HISTORY_DIR, f"{from_student_staff_number}_to_{to_student_staff_number}.txt")
    if not os.path.exists(chat_file):
        return []
    with open(chat_file, 'r', encoding='utf-8') as file:
        return file.read().splitlines()

@app.post('/signup')
async def signup(request: SignupRequest):
    if request.password != request.confirm_password:
        raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
    users = load_users()
    if request.student_staff_number in users:
        raise HTTPException(status_code=400, detail="이미 등록된 학번/교직원 번호입니다.")
    save_user(request.student_staff_number, request.username, request.password, request.email)
    return {"status": "success", "message": "회원가입 성공!"}

@app.post('/login')
async def login(request: LoginRequest):
    users = load_users()
    user = users.get(request.student_staff_number)
    if user and user['password'] == request.password:
        return {"status": "success", "message": "로그인 성공!", "username": user['username']}
    else:
        raise HTTPException(status_code=400, detail="로그인 실패! 학번/교직원 번호 또는 비밀번호가 잘못되었습니다.")

@app.get('/get_friends')
async def get_friends(student_staff_number: str = Query(..., alias="username")):
    friends = load_friends(student_staff_number)
    return {"friends": friends}

@app.post('/add_friend')
async def add_friend(request: AddFriendRequest):
    users = load_users()
    user = users.get(request.student_staff_number)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    friend = next((u for u in users.values() if u['username'] == request.friend_username), None)
    if not friend:
        raise HTTPException(status_code=404, detail="친구를 찾을 수 없습니다.")
    
    friends = load_friends(request.student_staff_number)
    if request.friend_username in friends:
        raise HTTPException(status_code=400, detail="이미 친구로 등록된 사용자입니다.")
    
    friends.append(request.friend_username)
    save_friends(request.student_staff_number, friends)
    return {"status": "success", "message": "친구 추가 성공"}

def send_password_email(email: str, password: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "luv.wlgjs@jj.ac.kr"
    smtp_password = "iiky iiox bxsl ygzr"

    msg = MIMEText(f"비밀번호는 다음과 같습니다: {password} \n비밀번호 수정을 원하시면 이 메일로 비밀번호와 함께 회신 바랍니다.")
    msg["Subject"] = "비밀번호 찾기 요청"
    msg["From"] = smtp_username
    msg["To"] = email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, email, msg.as_string())
        print("이메일이 성공적으로 전송되었습니다.")
    except Exception as e:
        print(f"이메일 전송 중 오류 발생: {e}")

@app.post('/password_reset')
async def password_reset(request: PasswordResetRequest):
    users = load_users()
    user_info = next((user for user in users.values() if user['email'] == request.email), None)
    if user_info:
        send_password_email(request.email, user_info['password'])
        return {"status": "success", "message": "비밀번호가 이메일로 전송되었습니다."}
    else:
        raise HTTPException(status_code=400, detail="등록되지 않은 이메일입니다.")

connected_users = {}

@sio.event
async def connect(sid, environ):
    logger.info(f'connect {sid}')

@sio.event
async def disconnect(sid):
    logger.info(f'disconnect {sid}')
    user_info = connected_users.pop(sid, None)
    if user_info:
        logger.info(f"User {user_info['username']} disconnected")

@sio.event
async def join(sid, data):
    username = data.get('username')
    student_staff_number = data.get('student_staff_number')

    if username is None or student_staff_number is None:
        await sio.emit('error', {
            'message': "username 또는 student_staff_number가 없습니다."
        }, to=sid)
        return

    connected_users[sid] = {'username': username, 'student_staff_number': student_staff_number}
    logger.info(f"User {username} joined with sid {sid}")
    logger.info(f"Current connected users: {connected_users}")

@sio.event
async def message(sid, data):
    try:
        to_username = data['to']
        message = data['message']
        from_username = connected_users[sid]['username']
        from_student_staff_number = connected_users[sid]['student_staff_number']
        
        logger.info(f"Received message from {from_username} to {to_username}: {message}")
        
        recipient = next((u for s, u in connected_users.items() if u['username'] == to_username), None)
        if recipient:
            recipient_sid = next(s for s, u in connected_users.items() if u['username'] == to_username)
            logger.info(f"Sending message to {recipient_sid}")
            await sio.emit('message', {
                'from': {
                    'username': from_username,
                    'student_staff_number': from_student_staff_number
                },
                'message': message
            }, to=recipient_sid)
            save_message(from_student_staff_number, recipient['student_staff_number'], message)
        else:
            logger.info(f"Recipient {to_username} not found. Current connected users: {connected_users}")
    except KeyError as e:
        logger.error(f"KeyError: {e}. SID: {sid}, Data: {data}")

@app.get('/get_chat_history')
async def get_chat_history(username: str, friend: str):
    users = load_users()
    user = next((u for u in users.values() if u['username'] == username), None)
    friend_user = next((u for u in users.values() if u['username'] == friend), None)
    
    if not user or not friend_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    chat_history = load_chat_history(user['student_staff_number'], friend_user['student_staff_number'])
    return {"chat_history": chat_history}

if __name__ == '__main__':
    uvicorn.run(socket_app, host='0.0.0.0', port=5000)
