import socket
import ssl
import threading

# Список всех подключенных клиентов и комнат
clients = {}
rooms = {}

def handle_client(client_socket, addr):
    print(f"Connected with {addr}")
    username = None
    current_room = None

    try:
        # Получаем имя пользователя из сертификата
        cert = client_socket.getpeercert()
        if not cert:
            client_socket.send("Client certificate is required".encode('utf-8'))
            return

        # Ищем имя пользователя (Common Name, CN) в сертификате
        for field in cert['subject']:
            for key, value in field:
                if key == 'commonName':
                    username = value
                    break
            if username:
                break

        if not username:
            client_socket.send("Username is required".encode('utf-8'))
            return

        # Сохраняем данные клиента в формате словаря
        clients[client_socket] = {'username': username, 'room': None}
        print(f"User {username} connected")

        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break

            print(f"Received data from {addr}: {data}")

            if data == "GET_ROOM_LIST":
                send_room_list(client_socket)
            elif data.startswith("CREATE_ROOM:"):
                room_name = data.split(":")[1]
                current_room = create_room(client_socket, room_name)
            elif data.startswith("JOIN_ROOM:"):
                room_name = data.split(":")[1]
                print(f"Joining room: {room_name}")
                current_room = join_room(client_socket, room_name)
            else:
                # Отправляем сообщение, если клиент находится в комнате
                if client_socket in clients and 'username' in clients[client_socket]:
                    if clients[client_socket]['room']:
                        # Форматируем сообщение
                        broadcast_message_in_room(data, clients[client_socket]['room'], client_socket)
                    else:
                        client_socket.send("Please join a room first.".encode('utf-8'))
                else:
                    print(f"Error: Client {client_socket} not found or missing username")

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        print(f"{addr} disconnected")
        if current_room:
            leave_room(client_socket, current_room)
        client_socket.close()
        if client_socket in clients:
            del clients[client_socket]

def join_room(client_socket, room_name):
    """Присоединение клиента к существующей комнате."""
    if room_name in rooms:
        rooms[room_name].append(client_socket)
        clients[client_socket]['room'] = room_name  # Обновляем комнату в словаре клиента
        client_socket.send(f"Joined room: {room_name}".encode('utf-8'))  # Уведомление клиента
        return room_name
    else:
        client_socket.send(f"Room '{room_name}' does not exist.".encode('utf-8'))
        return None

def create_room(client_socket, room_name):
    """Создание новой комнаты и присоединение к ней клиента."""
    if room_name not in rooms:
        rooms[room_name] = []
    rooms[room_name].append(client_socket)
    clients[client_socket]['room'] = room_name  # Обновляем комнату в словаре клиента
    print(f"Room '{room_name}' created and {client_socket.getpeername()} joined.")
    broadcast_room_list()
    return room_name

def leave_room(client_socket, room_name):
    """Клиент покидает комнату."""
    if room_name in rooms and client_socket in rooms[room_name]:
        rooms[room_name].remove(client_socket)
        if len(rooms[room_name]) == 0:
            del rooms[room_name]  # Удаляем комнату, если она пустая
        broadcast_room_list()

def send_room_list(client_socket):
    """Отправка списка комнат клиенту."""
    room_list_message = f"ROOM_LIST:{','.join(rooms.keys())}" if rooms else "ROOM_LIST:No rooms available"
    client_socket.send(room_list_message.encode('utf-8'))
    print(f"Sent room list to {client_socket.getpeername()}: {room_list_message}")

def broadcast_room_list():
    """Отправка обновленного списка комнат всем клиентам."""
    room_list_message = f"ROOM_LIST:{','.join(rooms.keys())}" if rooms else "ROOM_LIST:No rooms available"
    for client in clients.keys():
        try:
            client.send(room_list_message.encode('utf-8'))
            print(f"Sent updated room list to {client.getpeername()}")
        except Exception as e:
            print(f"Error sending room list to client: {e}")

def broadcast_message_in_room(message, room_name, sender_socket):
    """Отправка сообщения пользователям в комнате с указанием имени отправителя и названия комнаты."""
    if room_name in rooms:
        if sender_socket in clients and 'username' in clients[sender_socket]:
            sender_name = clients[sender_socket]['username']  # Получаем имя отправителя
            for client in rooms[room_name]:
                if client != sender_socket:
                    try:
                        # Форматируем сообщение с указанием комнаты
                        formatted_message = f"[{room_name}] {sender_name}: {message}"  # Добавляем название комнаты
                        client.send(formatted_message.encode('utf-8'))
                    except Exception as e:
                        print(f"Error sending message to client: {e}")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 5555))
    server_socket.listen()
    print("Server is listening on port 5555")

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile="ssl/server.crt", keyfile="ssl/server.key")
    context.load_verify_locations(cafile="ssl/ca.crt")
    context.verify_mode = ssl.CERT_REQUIRED

    while True:
        client_socket, addr = server_socket.accept()
        client_socket = context.wrap_socket(client_socket, server_side=True)
        clients[client_socket] = None  # Пока клиент не присоединился к комнате
        thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        thread.start()

if __name__ == "__main__":
    start_server()