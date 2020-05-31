"""C/S通信服务端"""

from socket import *
import threading
import struct


serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(5)


def send_yes(newSocket):
    try:
        newSocket.send(struct.pack("!cI", b'Y', 5))
    except:
        print("Send package failed, please try again.")


def send_no(newSocket):
    try:
        newSocket.send(struct.pack("!cI", b'N', 5))
    except:
        print("Send package failed, please try again.")


def send_file(filename, newSocket):
    newSocket.send(struct.pack("!cI", b'S', 5))
    with open(filename, 'rb') as f:
        while True:
            body = f.read(10235)
            if not body:
                newSocket.send(struct.pack("!cI", b'T', 5))
                break
            bodySize = len(body) + 5
            package = struct.pack("!cI", b'I', bodySize) + body
            newSocket.send(package)
            recv_data()
    print(f"Successfully sended.")


def recv_data(newSocket) -> tuple:
    recvBytes = newSocket.recv(1024)
    header = struct.unpack("!cI", recvBytes[:5])
    body = recvBytes[5:].decode()
    return (header, body)


def tcp_connect(newSocket, addr):
    package = recv_data(newSocket)
    send_yes(newSocket)
    print(f"Connection from {addr[0]}, port {addr[1]}.")
    while True:
        package = recv_data(newSocket)
        header = package[0]
        filename = package[1]
        if header[0] == b'S':
            global serverSocket
            send_yes(newSocket)
            newSocket.close()
            print(f"{addr[0]}, port {addr[1]} closed, program shutdown.")
            serverSocket.close()
            exit(0)
        elif header[0] == b'B':
            send_yes(newSocket)
            newSocket.close()
            print(f"{addr[0]}, port {addr[1]} closed.")
            break
        elif header[0] == b'D':
            try:
                open(filename, 'rb')
            except IOError:
                send_no(newSocket)
                continue
            send_yes(newSocket)
            if recv_data(newSocket)[0][0] == b'C':
                continue
            print(f"Sending file: {filename}")
            send_file(filename, newSocket)
    return True


def __main__():
    print("The server is ready to receive.")
    while True:
        try:
            newSocket, addr = serverSocket.accept()
        except OSError:
            exit(0)
        t = threading.Thread(target=tcp_connect, args=(newSocket, addr), name="main")
        t.start()


if __name__ == "__main__":
    __main__()
