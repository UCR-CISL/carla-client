# client.py
import zmq
import time
import random

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://192.168.88.97:5555")

# Simulate staggered client start
time.sleep(random.uniform(0.1, 2.0))

socket.send(b"OK")
reply = socket.recv()
print(f"Client received reply: {reply.decode()}")
