import zmq
    
class Server():
    def __init__(self, port="tcp://192.168.88.97:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(port) 

    def recv_send_message(self, outgoing, timeout=500):
        self.socket.RCVTIMEO = timeout
        try:
            message = self.socket.recv()
            decoded = message.decode('utf-8')
            
            if outgoing == "Recieved": 
                self.socket.send(b"Recieved")
                return decoded
            
            if outgoing == "terminate": 
                self.socket.send(b"terminate")
                return None
            
        except zmq.error.Again: 
            print(f"No message received within {timeout} seconds")
            return None

class Client():
    def __init__(self, port="tcp://192.168.88.97:5555"): 

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(port)

    def send(self, outgoing):
        print("SENDING READY")
        self.socket.send(outgoing.encode("utf-8"))

    def recv(self):
        print("RECEIVING READY")
        incoming = self.socket.recv()
        print("message", incoming)
        return incoming.decode('utf-8')