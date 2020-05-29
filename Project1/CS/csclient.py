"""C/S通信客户端"""

from socket import *
import struct


clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.settimeout(60)


def setup(serverIP, serverPort):
    global clientSocket
    try:
        clientSocket.connect((serverIP, serverPort))
        send_ok()
        message = clientSocket.recv(1024)
    except:
        print("Connection failed, please try again.")
        return
    if struct.unpack("!cI", message[:5]) == (b'Y', 5):
        print(f"Successfully connect to {serverIP}:{serverPort}.")
    else:
        print("Failed to confirm connect.")
        clientSocket.close()
        exit(1)


def send_filename(filename):
    global clientSocket
    body = filename.encode()
    bodySize = len(body) + 5
    statCode = b'D'
    package = struct.pack("!cI", statCode, bodySize) + body
    try:
        clientSocket.send(package)
        return clientSocket.recv(1024)
    except:
        print("Failed to send filename.")


def send_ok():
    global clientSocket
    try:
        clientSocket.send(struct.pack("!cI", b'A', 5))
    except:
        print("Send ACK package failed, please try again.")


def send_cancel():
    global clientSocket
    try:
        clientSocket.send(struct.pack("!cI", b'C', 5))
    except:
        print("Send Cancel package failed, please try again.")


def send_close():
    global clientSocket
    try:
        clientSocket.send(struct.pack("!cI", b'B', 5))
    except:
        print("Send Close package failed, please try again.")


def send_shutdown():
    global clientSocket
    try:
        clientSocket.send(struct.pack("!cI", b'S', 5))
    except:
        print("Send Shutdown package failed, please try again.")


def recv_file(filename):
    global clientSocket
    data = clientSocket.recv(1024)
    check_error(data[:5])
    if struct.unpack("!cI", data[:5])[0] != b'S':
        print("Something's wrong...")
        exit(1)
    print("Start downloading...")
    with open(filename, 'wb') as f:
        data = clientSocket.recv(10240)
        send_ok()
        while len(data) > 5:
            if struct.unpack("!cI", data[:5])[0] == b'T':
                break
            bodysize = struct.unpack("!cI", data[:5])[1]
            f.write(data[5:bodysize])
            data = clientSocket.recv(10240)
            send_ok()
    print("Successfully downloaded.")


def check_error(header):
    global clientSocket
    if struct.unpack("!cI", header) == (b'E', 5):
        print("Server error, closing...")
        clientSocket.close()
        exit(1)


def __main__():
    global clientSocket
    serverIP = str(input("Please input server IP: "))
    serverPort = int(input("Please input server port: "))
    setup(serverIP, serverPort)

    while True:
        filename = str(input("Please input file name, or 'q' to exit: "))
        if filename == 'q':
            print("Closing...")
            send_close()
            clientSocket.recv(1024)
            clientSocket.close()
            break
        elif filename == 's':
            print("Closing...")
            send_shutdown()
            clientSocket.recv(1024)
            clientSocket.close()
            break
        fileStat = send_filename(filename)
        check_error(fileStat[:5])
        if struct.unpack("!cI", fileStat[:5]) == (b'Y', 5):
            print("File exists. Do you want to download it?")
            op = input(
                "Input 'Y' or 'y' to continue, or other charactors to cancel:")
            if op not in ('Y', 'y'):
                send_cancel()
                print('Canceled.')
            else:
                send_ok()
                recv_file(filename)
        elif struct.unpack("!cI", fileStat[:5]) == (b'N', 5):
            print("File doesn't exist.")


if __name__ == "__main__":
    __main__()
