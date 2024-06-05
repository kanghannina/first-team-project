import customtkinter as ctk
import socketio
import requests
import os

class Inbox:
    def __init__(self, parent, username, user_fullname):
        self.parent = parent
        self.username = username
        self.user_fullname = user_fullname
        self.friends = []
        self.app_running = True
        self.current_friend = None
        self.sio = socketio.Client()
        self.chat_history_dir = os.path.join(os.path.dirname(__file__), 'chat_history')

        if not os.path.exists(self.chat_history_dir):
            os.makedirs(self.chat_history_dir)

        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('message', self.on_message)

        self.sio.connect('http://61.255.152.191:5000')  # 서버 주소로 변경

        self.create_inbox_window()

    def on_connect(self):
        print('Connected to server')
        self.sio.emit('join', {'username': self.user_fullname, 'student_staff_number': self.username})

    def on_disconnect(self):
        print('Disconnected from server')

    def on_message(self, data):
        sender = data['from']['username']
        message = data['message']
        self.show_message(sender, message)
        self.save_message(data['from']['student_staff_number'], self.current_friend, message)

    def create_inbox_window(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.parent.title("메일함 - 전주대학교 메일")
        self.parent.geometry("800x600")
        self.parent.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.parent.resizable(False, False)

       # Header
        header_frame = ctk.CTkFrame(self.parent, height=50, fg_color="#78aedd")
        header_frame.pack(side="top", fill="x")
        header_label = ctk.CTkLabel(header_frame, text=f"반갑습니다 {self.user_fullname}!", text_color="white", font=ctk.CTkFont(size=20, weight="bold"))
        header_label.pack(pady=10)

        # Main Content
        main_frame = ctk.CTkFrame(self.parent)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Sidebar
        sidebar_frame = ctk.CTkFrame(main_frame, width=200, fg_color="#f7f7f7")
        sidebar_frame.pack(side="left", fill="y", padx=(0, 10))

        menu_label = ctk.CTkLabel(sidebar_frame, text="Friends", font=ctk.CTkFont(size=15))
        menu_label.pack(pady=10)

        # Friend List Frame
        self.friend_list_frame = ctk.CTkFrame(sidebar_frame, fg_color="white")
        self.friend_list_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Add Friend Button
        add_friend_button = ctk.CTkButton(sidebar_frame, text="친구 추가", command=self.add_friend)
        add_friend_button.pack(pady=5, fill="x")

        # Chat Content
        content_frame = ctk.CTkFrame(main_frame, fg_color="#ffffff")
        content_frame.pack(expand=True, fill="both")

        self.chat_listbox = ctk.CTkTextbox(content_frame, state='disabled')
        self.chat_listbox.pack(expand=True, fill="both", padx=10, pady=10)

        # Message Entry
        self.message_entry = ctk.CTkEntry(content_frame)
        self.message_entry.pack(side="left", fill="x", padx=(10, 0), pady=10, expand=True)

        send_button = ctk.CTkButton(content_frame, text="전송", command=self.send_message)
        send_button.pack(side="right", padx=10, pady=10)

        self.load_friends()

    def add_friend(self):
        friend_name = self.custom_input_dialog("친구 추가", "친구의 사용자 이름을 입력하세요:")
        if friend_name:
            data = {"student_staff_number": self.username, "friend_username": friend_name}
            response = requests.post(f"http://61.255.152.191:5000/add_friend", json=data)
            if response.status_code == 200:
                self.friends.append(friend_name)
                self.update_friend_list()
            else:
                error_detail = response.json().get("detail", "친구 추가에 실패했습니다.")
                self.show_alert(error_detail)

    def send_message(self):
        message = self.message_entry.get()
        print(f"Attempting to send message: {message} to {self.current_friend}")
        if message and self.current_friend:
            self.sio.emit('message', {'to': self.current_friend, 'message': message})
            self.show_message(self.user_fullname, message)
            self.save_message(self.username, self.current_friend, message)
            self.message_entry.delete(0, 'end')
        else:
            self.show_alert("메시지를 입력하세요 또는 친구를 선택하세요.")

    def show_message(self, sender, message):
        self.chat_text.insert('end', f"{sender}: {message}\n")
        self.chat_text.yview('end')

    def save_message(self, from_student_staff_number, to_student_staff_number, message):
        chat_file = os.path.join(self.chat_history_dir, f"{from_student_staff_number}_to_{to_student_staff_number}.txt")
        with open(chat_file, 'a', encoding='utf-8') as file:
            file.write(f"{self.user_fullname}: {message}\n")

    def load_chat_history(self, friend):
        self.chat_text.delete('1.0', 'end')
        chat_file = os.path.join(self.chat_history_dir, f"{self.username}_to_{friend}.txt")
        if os.path.exists(chat_file):
            with open(chat_file, 'r', encoding='utf-8') as file:
                chat_history = file.read()
                self.chat_text.insert('end', chat_history)
                self.chat_text.yview('end')

    def load_friends(self):
        response = requests.get(f"http://61.255.152.191:5000/get_friends", params={"username": self.username})
        if response.status_code == 200:
            self.friends = response.json().get("friends", [])
            self.update_friend_list()
        else:
            self.show_alert("친구 목록을 불러오는데 실패했습니다.")

    def update_friend_list(self):
        for widget in self.friend_list_frame.winfo_children():
            widget.destroy()

        for friend in self.friends:
            friend_button = ctk.CTkButton(self.friend_list_frame, text=friend, command=lambda f=friend: self.select_friend(f))
            friend_button.pack(pady=5, fill="x")

    def select_friend(self, friend):
        self.current_friend = friend
        self.load_chat_history(friend)

    def custom_input_dialog(self, title, prompt):
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(title)
        dialog.geometry("300x150")

        label = ctk.CTkLabel(dialog, text=prompt, font=ctk.CTkFont(size=16, weight="bold"))
        label.pack(pady=20)

        entry = ctk.CTkEntry(dialog)
        entry.pack(pady=5)

        def on_submit():
            self.input_result = entry.get()
            dialog.destroy()

        submit_button = ctk.CTkButton(dialog, text="확인", command=on_submit)
        submit_button.pack(pady=10)

        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)

        dialog.update_idletasks()
        parent_window = self.parent.winfo_toplevel()
        window_width = dialog.winfo_width()
        window_height = dialog.winfo_height()
        screen_width = parent_window.winfo_screenwidth()
        screen_height = parent_window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.parent.wait_window(dialog)
        return self.input_result
    
    def show_alert(self, message):
        if self.app_running:
            try:
                alert = ctk.CTkToplevel(self.parent)
                alert.title("경고")
                alert.geometry("300x150")

                alert_label = ctk.CTkLabel(alert, text=message, font=ctk.CTkFont(size=16, weight="bold"))
                alert_label.pack(pady=20)

                close_button = ctk.CTkButton(alert, text="닫기", command=alert.destroy)
                close_button.pack(pady=20)

                alert.transient(self.parent)
                alert.grab_set()
                alert.lift()
                alert.attributes('-topmost', True)
                alert.resizable(False, False)

                alert.update_idletasks()
                parent_window = self.parent.winfo_toplevel()
                window_width = alert.winfo_width()
                window_height = alert.winfo_height()
                screen_width = parent_window.winfo_screenwidth()
                screen_height = parent_window.winfo_screenheight()
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                alert.geometry(f"{window_width}x{window_height}+{x}+{y}")
            except Exception as e:
                print(f"Alert 창을 생성하는 동안 오류 발생: {e}")
    
    def show_message(self, sender, message):
        self.chat_listbox.configure(state='normal')
        self.chat_listbox.insert("end", f"{sender}: {message}\n")
        self.chat_listbox.configure(state='disabled')

    def select_friend(self, friend):
        self.current_friend = friend
        self.chat_listbox.configure(state='normal')
        self.chat_listbox.delete("1.0", "end")
        self.chat_listbox.configure(state='disabled')
        print(f"Selected friend: {self.current_friend}")

    def on_closing(self):
        self.app_running = False
        self.sio.disconnect()
        self.parent.destroy()
