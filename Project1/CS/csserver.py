"""C/S通信服务端"""

from socket import *
import time
import struct


serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM)


def send_yes():
    global serverSocket
    try:
        serverSocket.send(struct.pack("!cI", b'Y', 5))
    except:
        print("Send package failed, please try again.")


def send_no():
    global serverSocket
    try:
        serverSocket.send(struct.pack("!cI", b'N', 5))
    except:
        print("Send package failed, please try again.")


def send_file(filename):
    global serverSocket
    with open(filename, 'rb') as f:
        while True:
            body = f.read(10235)
            if not body:
                serverSocket.send(struct.pack("!cI", b'T', 5))
                break
            bodySize = len(body) + 5
            package = struct.pack("!cI", b'I', bodySize) + body
            serverSocket.send(package)


def recv_data() -> tuple:
    global serverSocket
    recvBytes = serverSocket.recv(1024)
    header = struct.unpack(recvBytes[:5])
    body = recvBytes[5:].decode()
    return (header, body)


serverSocket.bind(('', serverPort))
serverSocket.listen(1)
print("The server is ready to receive.")

while True:
    serverSocket, addr = serverSocket.accept()
    package = recv_data()
    header = package[0]
    filename = package[1]
    if header[0] == b'B':
        break
    elif header[0] == b'D':
        try:
            open(filename, 'rb')
        except IOError:
            send_no()
            continue
        send_yes()
        if recv_data()[0][0] == b'C':
            continue
        send_file(filename)
    
serverSocket.close()
