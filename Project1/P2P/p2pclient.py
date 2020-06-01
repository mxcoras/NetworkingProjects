"""P2P通信客户端"""

from socket import *
import struct
import threading
import json


clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.settimeout(60)
fileSocket = socket(AF_INET, SOCK_DGRAM)
fileSocket.bind(('', 12000))
chatSocket = socket(AF_INET, SOCK_DGRAM)
chatSocket.bind(('', 12001))


def recv_data() -> tuple:
    recvBytes = clientSocket.recv(4096)
    header = struct.unpack("!cI", recvBytes[:5])
    body = recvBytes[5:].decode()
    return (header[0], body)


def thr_error(header, target, addr):
    if header != target:
        conn_fail(addr)


def check_header(header, target=b'Y'):
    if header != target:
        return False
    return True


def send_on(addr):
    try:
        clientSocket.connect(addr)
        clientSocket.send(struct.pack("!cI", b'O', 5))
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)
    print(f"Successfully connect to {addr[0]}:{addr[1]}.")


def send_off(addr):
    try:
        clientSocket.send(struct.pack("!cI", b'F', 5))
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)


def send_ok(addr):
    try:
        clientSocket.send(struct.pack("!cI", b'A', 5))
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)


def send_shutdown(addr):
    try:
        clientSocket.send(struct.pack("!cI", b'S', 5))
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)


def update_file(filename, addr):
    try:
        f = open(filename, 'rb')
    except IOError:
        print("No such file.")
        return
    filesize = len(f)
    body = str((filename, filesize)).encode()
    bodySize = len(body) + 5
    statCode = b'D'
    package = struct.pack("!cI", statCode, bodySize) + body
    try:
        clientSocket.send(package)
        flag = check_header(recv_data()[0])
    except:
        conn_fail(addr)
    if flag:
        print("Successfully updated.")
    else:
        print("Failed to update.")


def del_file(filename, addr):
    body = filename.encode()
    bodySize = len(body) + 5
    statCode = b'X'
    package = struct.pack("!cI", statCode, bodySize) + body
    try:
        clientSocket.send(package)
        flag = check_header(recv_data()[0])
    except:
        conn_fail(addr)
    if flag:
        print("Successfully deleted.")
    else:
        print("Failed to delete.")


def get_finfo(addr):
    package = struct.pack("!cI", b'G', 5)
    try:
        clientSocket.send(package)
        raw = recv_data()
    except:
        conn_fail(addr)
    header = raw[0]
    body = raw[1]
    if check_header(header[0], b'N'):
        print("No such file.")
        return None
    return json.loads(body)


def recv_file(finfo:dict):
    pass


def get_peers(addr):
    package = struct.pack("!cI", b'P', 5)
    try:
        clientSocket.send(package)
        raw = recv_data()
    except:
        conn_fail(addr)
    header = raw[0]
    body = raw[1]
    if check_header(header[0], b'N'):
        print("Failed to load peer list.")
        return
    plist = json.loads(body)
    peers = plist.get("peers", default=[])
    for peer in peers:
        print(peer)


def start_chat():
    t = threading.Thread(target=recv_msg)
    t.setDaemon(True)
    t.start()
    toip = str(input("Please input target IP: "))
    toport = int(input("Please input target port: "))
    i = 1
    while True:
        msg = str(input("Please input message, or '!q' to exit: \n"))
        if msg == '!q':
            return
        msgBody = msg.encode()
        packlen = len(msgBody) + 9
        msgHeader = struct.pack("!cII", b'M', i, packlen)
        chatSocket.sendto(msgHeader + msgBody, (toip, toport))
        print(f"Sended to {toip}:{toport}")


def recv_msg():
    while True:
        try:
            package, serverAddr = chatSocket.recvfrom(2048)
        except:
            print("[Warning]: Chat socket closed.")
            return
        msgBody = package[9:].decode()
        print(
            f"\nMessage from {serverAddr[0]}:{serverAddr[1]}: \n{msgBody}\n\nPlease input message, or '!q' to exit: ")


def conn_fail(addr):
    print(f"Connection failed with tracker {addr[0]}:{addr[1]}")
    clientSocket.close()
    fileSocket.close()
    chatSocket.close()
    exit(0)


def conn_close(addr):
    clientSocket.close()
    fileSocket.close()
    chatSocket.close()
    print(f"Connection closed with tracker {addr[0]}:{addr[1]}")
    exit(0)


def print_help():
    print("Command list:")
    print("update [filename]\nReport new file to your tracker.")
    print("delet [filename]\nReport removed file to your tracker.")
    print("get [filename]\nGet peer list of file.")
    print("getpeer\nGet full peer list and print.")
    print("chat\nStart chatting mode.")
    print("close\nClose connection.")
    print("shutdown\nClose connection and shutdown tracker.")


def __main__():
    serverIP = str(input("Please input tracker IP: "))
    serverPort = int(input("Please input tracker port: "))
    addr = (serverIP, serverPort)
    send_on(addr)
    hint = "Please input command, use 'help' to get help info:"
    while True:
        print(hint)
        raw = input('$> ')
        args = raw.split(' ')
        argnum = len(args) - 1
        command = args[0]
        if command == 'update' and argnum == 1:
            update_file(args[1], addr)
        elif command == 'delet' and argnum == 1:
            del_file(args[1], addr)
        elif command == 'get' and argnum == 1:
            finfo = get_finfo(addr)
            if finfo != None:
                recv_file(finfo)
        elif command == 'getpeer':
            get_peers(addr)
        elif command == 'chat':
            start_chat()
        elif command == 'close':
            send_off(addr)
        elif command == 'shutdown':
            send_shutdown(addr)
        elif command == 'help':
            print_help()
        else:
            print("Command error. Use 'help' to get help info.")


if __name__ == "__main__":
    __main__()
