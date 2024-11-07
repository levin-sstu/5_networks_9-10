import socket
import ssl
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, StringVar, OptionMenu
import sys

class ChatClient:
    def __init__(self, master, certfile, keyfile):
        self.master = master
        self.master.title("Chat Client")

        # Текущее имя пользователя
        self.username = simpledialog.askstring("Username", "Enter your name:", parent=self.master)
        if not self.username:
            messagebox.showerror("Error", "Username is required!")
            self.master.destroy()
            return  # Остановите выполнение, если имя не введено

        self.username_label = tk.Label(master, text=f"Username: {self.username}")
        self.username_label.pack(pady=5)

        # Текущая комната
        self.current_room_label = tk.Label(master, text="Current Room: No room")
        self.current_room_label.pack(pady=5)

        # Интерфейс для комнаты
        self.room_label = tk.Label(master, text="Choose or create a room")
        self.room_label.pack(pady=5)

        # Поле для ввода новой комнаты
        self.room_entry = tk.Entry(master, width=50)
        self.room_entry.pack(pady=5)

        # Кнопка для создания комнаты
        self.create_room_button = tk.Button(master, text="Create Room", command=self.create_room)
        self.create_room_button.pack(pady=5)

        # Меню для выбора комнаты
        self.selected_room = StringVar(master)
        self.selected_room.set("No rooms available")
        self.room_list_menu = OptionMenu(master, self.selected_room, "No rooms available")
        self.room_list_menu.pack(pady=5)

        # Кнопка для входа в комнату
        self.join_room_button = tk.Button(master, text="Join Room", command=self.join_room)
        self.join_room_button.pack(pady=5)

        # Поле для чата
        self.chat_display = tk.Text(master, state='disabled', width=50, height=20)
        self.chat_display.pack(pady=10)

        self.message_entry = tk.Entry(master, width=50)
        self.message_entry.pack(pady=10)
        self.message_entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(master, text="Send", command=self.send_message)
        self.send_button.pack(pady=5)

        # Подключение к серверу
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        context.load_verify_locations(cafile="ssl/ca.crt")

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = context.wrap_socket(self.client_socket, server_hostname='localhost')
        self.client_socket.connect(('localhost', 5555))

        # Запрос списка комнат после подключения
        self.client_socket.send("GET_ROOM_LIST".encode('utf-8'))

        # Поток для обработки входящих сообщений
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.start()

    def create_room(self):
        room_name = self.room_entry.get()
        if room_name:
            self.client_socket.send(f"CREATE_ROOM:{room_name}".encode('utf-8'))
            self.room_entry.delete(0, tk.END)  # Очищаем поле для ввода

    def join_room(self):
        room_name = self.selected_room.get()
        if room_name and room_name != "No rooms available":
            self.client_socket.send(f"JOIN_ROOM:{room_name}".encode('utf-8'))
            # Обновляем метку текущей комнаты сразу
            self.current_room_label.config(text=f"Current Room: {room_name}")

    def send_message(self, event=None):
        message = self.message_entry.get()
        if message:
            room_name = self.selected_room.get()
            formatted_message = f"{self.username}: {message}"
            self.client_socket.send(formatted_message.encode('utf-8'))

            # Логируем, в какую комнату отправлено сообщение
            self.display_message(
                f"[{room_name}] {formatted_message}")  # Отображаем отправленное сообщение с информацией о комнате
            self.message_entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message.startswith("ROOM_LIST:"):
                    rooms = message.split(":")[1].split(",") if message != "ROOM_LIST:No rooms available" else [
                        "No rooms available"]
                    self.update_room_list(rooms)
                elif message.startswith("Joined room:"):
                    self.current_room_label.config(text=message)
                else:
                    # Просто отображаем сообщение
                    self.display_message(message)  # Показать сообщение в чате
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def update_room_list(self, rooms):
        menu = self.room_list_menu["menu"]
        menu.delete(0, "end")  # Очищаем меню
        for room in rooms:
            menu.add_command(label=room, command=lambda value=room: self.selected_room.set(value))
        self.selected_room.set(rooms[0])  # Устанавливаем выбранную комнату

    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"{message}\n")
        self.chat_display.config(state='disabled')

    def on_closing(self):
        self.client_socket.close()
        self.master.destroy()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py <certfile> <keyfile>")
        sys.exit(1)

    certfile = sys.argv[1]
    keyfile = sys.argv[2]

    root = tk.Tk()
    chat_client = ChatClient(root, certfile, keyfile)
    root.protocol("WM_DELETE_WINDOW", chat_client.on_closing)
    root.mainloop()