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
    if struct.unpack(message[:5]) == ('Y',5):
        print(f"Successfuly connect to {serverIP}:{serverPort}.")
    else:
        print("Failed to confirm connect.")
        clientSocket.close()
        exit(1)


def send_filename(filename):
    global clientSocket
    body = struct.pack("!s", filename.encode())
    bodySize = len(body)
    statCode = b'A'
    header = struct.pack("!cI", statCode, bodySize)
    try:
        clientSocket.send(header + body)
        return clientSocket.recv(1024)
    except:
        print("Failed to send filename.")


def send_ok():
    global clientSocket
    try:
        clientSocket.send(struct.pack("!cI", b'A', 5))
    except:
        print("Send OK package failed, please try again.")


def send_cancel():
    global clientSocket
    try:
        clientSocket.send(struct.pack("!cI", b'C', 5))
    except:
        print("Send Cancel package failed, please try again.")


def recv_file(filename):
    global clientSocket
    firstData = clientSocket.recv(1024)
    # 待完善
    pass


def check_error(header):
    global clientSocket
    if struct.unpack(header) == ('E', 5):
        print("Server error, closing...")
        clientSocket.close()
        exit(1)


serverIP = str(input("Please input server IP: "))
serverPort = int(input("Please input server port: "))
setup(serverIP, serverPort)

while True:
    filename = str(input("Please input file name, or 'q' to exit: "))
    if filename == 'q':
        break
    fileStat = send_filename(filename)
    check_error(fileStat[:5])
    if struct.unpack(fileStat[:5]) == ('Y', 5):
        print("File exists. Do you want to download it?")
        op = input("Input 'Y' or 'y' to continue, or other charactors to cancel:")
        if op not in ('Y', 'y'):
            send_cancel()
            print('Canceled.')
        else:
            send_ok()
            print('Start downloading...')
            recv_file(filename)
    elif struct.unpack(fileStat[:5]) == ('N', 5):
        print("File doesn't exist.")

print("Closing...")
clientSocket.close()
