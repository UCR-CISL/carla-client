import zmq
    
class Server():
    def __init__(self, port="tcp://localhost:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
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
    def __init__(self, port="tcp://localhost:5555"): 

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(port)

    def recv_send_message(self, outgoing):
        self.socket.send(outgoing.encode("utf-8"))
        incoming = self.socket.recv()
        return incoming.decode('utf-8')