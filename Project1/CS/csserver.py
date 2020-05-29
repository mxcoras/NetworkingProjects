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
    serverSocket.send(struct.pack("!cI", b'S', 5))
    with open(filename, 'rb') as f:
        while True:
            body = f.read(10235)
            if not body:
                serverSocket.send(struct.pack("!cI", b'T', 5))
                break
            bodySize = len(body) + 5
            package = struct.pack("!cI", b'I', bodySize) + body
            serverSocket.send(package)
            recv_data()
    print(f"Successfully sended.")


def recv_data() -> tuple:
    global serverSocket
    recvBytes = serverSocket.recv(1024)
    header = struct.unpack("!cI", recvBytes[:5])
    body = recvBytes[5:].decode()
    return (header, body)


def __main__():
    global serverSocket
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(1)
    print("The server is ready to receive.")
    serverSocket, addr = serverSocket.accept()
    package = recv_data()
    send_yes()
    print(f"Connection from {addr[0]}, port {addr[1]}.")
    while True:
        package = recv_data()
        header = package[0]
        filename = package[1]
        if header[0] == b'S':
            send_yes()
            serverSocket.close()
            print(f"{addr[0]}, port {addr[1]} closed, program shutdown.")
            return False
        elif header[0] == b'B':
            send_yes()
            serverSocket.close()
            print(f"{addr} Closed.")
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
            print(f"Sending file: {filename}")
            send_file(filename)
    return True


if __name__ == "__main__":
    flag = True
    while flag:
        flag = __main__()
    serverSocket.close()
