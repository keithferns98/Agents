import socket
import threading

HOST = "0.0.0.0"
PORT = 8585

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    clients.append(conn)

    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            message =data.decode()
            print(f"[{addr}] {message}")

            # Broadcast to all clients
            for client in clients:
                # if client != conn:
                    client.sendall(f"{addr}: {message}".encode())

    except:
        pass

    print(f"[DISCONNECTED] {addr}")
    clients.remove(conn)
    conn.close()

while True: 
    conn, addr = server.accept() 
    thread = threading.Thread(target=handle_client, args=(conn, addr)) 
    thread.start()