"""C/S通信客户端"""

from socket import *
import struct
import threading


clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.settimeout(60)
chatSocket = socket(AF_INET, SOCK_DGRAM)
chatSocket.bind(('', 12001))


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


def start_chat(serverAddr):
    global chatSocket
    t = threading.Thread(target=recv_msg)
    t.setDaemon(True)
    t.start()
    toip = str(input("Please input target IP: "))
    toip = ntohl(struct.unpack("I", inet_aton(toip))[0])
    toport = int(input("Please input target port: "))
    msgHeader = struct.pack("!II", toip, toport)
    while True:
        msg = str(input("Please input message, or '!q' to exit: \n"))
        if msg == '!q':
            return
        msgBody = msg.encode()
        chatSocket.sendto(msgHeader + msgBody, serverAddr)
        print(f"Sended to {serverAddr[0]}:{serverAddr[1]}")


def recv_msg():
    global chatSocket
    while True:
        try:
            package, serverAddr = chatSocket.recvfrom(2048)
        except:
            print("[Warning]: Chat socket closed.")
            return
        addrInfo = struct.unpack("!II", package[:8])
        fromip = inet_ntoa(struct.pack('I', htonl(addrInfo[0])))
        fromport = addrInfo[1]
        msgBody = package[8:].decode()
        print(
            f"\nMessage from {fromip}:{fromport}: \n{msgBody}\n\nPlease input message, or '!q' to exit: ")


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
        filename = str(input("Please input file name, \nor 'c' to start chat, 'q' to exit: \n"))
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
        elif filename == 'c':
            start_chat((serverIP, serverPort))
            continue
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
