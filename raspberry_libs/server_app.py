import serial
import time
import socket
import threading
import smbus

class Server:
    """ Class to manage TCP server communication."""
    def __init__(self):
        """ Initializes the Server class with a None connection object. """
        self.conn = None  # connection object for the client

    def get_local_ip(self):
        """ Retrieves the local IP address of the device by attempting to connect to an external server.
        :return: the local IP address as a string, or None if it cannot be determined. """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # create a UDP socket object
            s.connect(("8.8.8.8", 80))                               # connect to an external server to get local IP
            local_ip = s.getsockname()[0]                            # get the local IP address from the socket
            s.close()
            return local_ip
        except socket.error:
            return None # return None if IP cannot be determined

    def init_server(self):
        """ Initializes the TCP server, binds it to the local IP and a predefined port and listens for and accepts an incoming client connection. """
        self.HOST = self.get_local_ip() # get local IP address
        self.PORT = 1234 # port for communication
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # create a TCP/IP socket
          s.bind((self.HOST, self.PORT)) # bind the socket to the host and port
          s.listen(5) # allowing up to 5 queued connections
          self.conn, addr = s.accept() # accept a new connection
          print('Connect')

    def data_from_client(self):
        """ Receive data from client """
        while True:
            try:
                data1 = self.conn.recv(1024) # receive up to 1024 bytes of data
                if data1 == 1:
                    print('correct server')
            except Exception as e:
                print('Error in receiving data from client:',e)
    def send_to_client(self,data,data1,data2):
        """ Sends data to the connected client. The data is formatted as a tuple, encoded to UTF-8, and then transmitted.
        :param data: The first piece of data to send.
        :param data1: The second piece of data to send.
        :param data2: The third piece of data to send.
        """
        try:
            self.conn.sendall(str((data,data1,data2)).encode('utf-8')) # send the tuple (data, data1, data2) as a UTF-8 string
        except Exception as e:
            print('Error in sending data to client:',e)
