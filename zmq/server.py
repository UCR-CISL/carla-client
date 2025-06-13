# server.py
import zmq

context = zmq.Context()
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://192.168.88.97:5555")

print("Server is ready...")

while True:
    # ROUTER receives: [client_id, empty, message]
    client_id, empty, message = socket.recv_multipart()
    print(f"Received from {client_id}: {message.decode()}")

    if message == b"OK":
        socket.send_multipart([client_id, b'', b"ACK"])
