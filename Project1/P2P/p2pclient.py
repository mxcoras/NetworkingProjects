"""P2P通信客户端"""

from socket import *
import struct
import threading
import json
from random import randint
from os import remove


SEED_PORT = 12000
CHAT_PORT = 12001

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.settimeout(60)
seedSocket = socket(AF_INET, SOCK_DGRAM)
seedSocket.bind(('', SEED_PORT))
chatSocket = socket(AF_INET, SOCK_DGRAM)
chatSocket.bind(('', CHAT_PORT))


thread_list = []


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
        body = str(CHAT_PORT).encode()
        plen = len(body) + 5
        clientSocket.send(struct.pack("!cI", b'O', plen) + body)
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)
    print(f"Successfully connect to {addr[0]}:{addr[1]}.")


def send_off(addr):
    try:
        body = str(CHAT_PORT).encode()
        plen = len(body) + 5
        clientSocket.send(struct.pack("!cI", b'F', plen) + body)
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)
    exit(0)


def send_ok(addr):
    try:
        clientSocket.send(struct.pack("!cI", b'A', 5))
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)


def send_shutdown(addr):
    try:
        body = str(CHAT_PORT).encode()
        plen = len(body) + 5
        clientSocket.send(struct.pack("!cI", b'S', plen) + body)
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)
    exit(0)


def update_file(filename, addr):
    try:
        f = open(filename, 'rb')
    except IOError:
        print("No such file.")
        return
    data = f.read()
    filesize = len(data)
    body = str((filename, filesize, SEED_PORT)).encode()
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


def get_finfo(filename, addr):
    package = struct.pack("!cI", b'G', 5) + filename.encode()
    try:
        clientSocket.send(package)
        raw = recv_data()
    except:
        conn_fail(addr)
    header = raw[0]
    body = raw[1]
    if check_header(header, b'N'):
        print("No such file.")
        return None
    return json.loads(body)


def recv_file(filename, finfo: dict):
    peers = finfo.get("peers", [])
    if len(peers) == 1:
        recv_from_peers(tuple(peers[0]), filename, 0)
    elif len(peers) == 2:
        for i in range(2):
            t = threading.Thread(target=recv_from_peers, args=(tuple(peers[i]), filename, i+1))
            t.setDaemon(True)
            t.start()
            thread_list.append(t)
        for j in thread_list:
            j.join()
        part1 = open(filename + '.1', 'rb')
        part2 = open(filename + '.2', 'rb')
        with open(filename, 'wb') as f:
            f.write(part1.read())
            f.write(part2.read())
        part1.close()
        remove(filename + '.1')
        part2.close()
        remove(filename + '.2')
    print(f"Successful download {filename}")


def recv_from_peers(peer, filename, part):
    leechSocket = socket(AF_INET, SOCK_DGRAM)
    leechSocket.settimeout(15)
    body = filename.encode()
    pLen = len(body) + 9
    leechSocket.sendto(struct.pack("!cII", b'G', part, pLen) + body, peer)
    try:
        package, serverAddr = leechSocket.recvfrom(2048)
    except:
        print("[Error]: Leech socket closed.\n>$ ", end='')
        return
    header = struct.unpack("!cII", package[:9])
    if not check_header(header[0], b'S'):
        print("No such file from peers.\n>$ ", end='')
        return
    else:
        leechSocket.sendto(struct.pack("!cII", b'A', 0, 9), peer)
    if part != 0:
        fix = f".{part}"
        f = open(filename + fix, 'wb')
    else:
        f = open(filename, 'wb')
    i = 1
    while True:
        try:
            package, serverAddr = leechSocket.recvfrom(10240)
        except:
            print("[Error]: Leech socket closed.\n>$ ", end='')
            return
        header = struct.unpack("!cII", package[:9])
        body = package[9:]
        if check_header(header[0], b'I') and header[1] == i:
            leechSocket.sendto(struct.pack("!cII", b'A', i, 9), peer)
            f.write(body)
            i += 1
            continue
        elif check_header(header[0], b'T'):
            f.close()
            leechSocket.sendto(struct.pack("!cII", b'A', 0, 9), peer)
            return
        else:
            print("[Error]: Leech socket closed by peer.\n>$ ", end='')
            return


def get_peers(addr):
    package = struct.pack("!cI", b'P', 5)
    try:
        clientSocket.send(package)
        raw = recv_data()
    except:
        conn_fail(addr)
    header = raw[0]
    body = raw[1]
    if check_header(header, b'N'):
        print("Failed to load peer list.")
        return
    plist = json.loads(body)
    peers = plist.get("peers", [])
    for peer in peers:
        print(peer)
    print(">$ ", end='')


def start_seed():
    while True:
        try:
            package, peerAddr = seedSocket.recvfrom(2048)
            header = struct.unpack("!cII", package[:9])
            if check_header(header[0], b'G'):
                body = package[9:].decode()
                print(f"{peerAddr} in.\n$> ", end='')
                send_file(peerAddr, body, header[1])
        except:
            print("[Warning]: Seed socket closed.\n>$ ", end='')
            return


def send_file(peerAddr, filename, part):
    try:
        open(filename, 'rb')
    except IOError:
        seedSocket.sendto(struct.pack("!cII", b'E', 0, 9), peerAddr)
        return
    with open(filename, 'rb') as f:
        data = f.read()
        size = len(data)
        bodybytes = b''
        f.seek(0)
        if part == 0:
            bodybytes = f.read()
        elif part == 1:
            bodybytes = f.read(int(size/2))
        elif part == 2:
            f.read(int(size/2))
            bodybytes = f.read()
    seedSocket.sendto(struct.pack("!cII", b'S', 0, 9), peerAddr)
    if not recv_ack(peerAddr, 0):
        return
    fix = randint(1, 1000)
    with open('TEMP.'+str(fix), 'wb+') as sf:
        sf.write(bodybytes)
        sf.seek(0)
        packnum = 1
        while True:
            body = sf.read(10231)
            if not body:
                seedSocket.sendto(struct.pack("!cII", b'T', 0, 9), peerAddr)
                print(f"Send {filename} to {peerAddr} complete.\n>$ ", end='')
                if not recv_ack(peerAddr, 0):
                    print("[Warnig] Complete ACK not recieved.")
                sf.close()
                remove('TEMP.'+str(fix))
                return
            bodySize = len(body) + 9
            package = struct.pack("!cII", b'I', packnum, bodySize) + body
            seedSocket.sendto(package, peerAddr)
            if not recv_ack(peerAddr, packnum):
                print("OOS")
                sf.close()
                remove('TEMP.'+str(fix))
                return
            packnum += 1
    sf.close()
    remove('TEMP.'+str(fix))


def recv_ack(peerAddr, num):
    try:
        package, peerAddr = seedSocket.recvfrom(2048)
        header = struct.unpack("!cII", package[:9])
    except:
        print(f"Peer {peerAddr[0]}:{peerAddr[1]} timeout.")
        return False
    if check_header(header[0], b'A') and header[1] == num:
        return True
    else:
        return False


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
    seedSocket.close()
    chatSocket.close()
    exit(0)


def conn_close(addr):
    clientSocket.close()
    seedSocket.close()
    chatSocket.close()
    print(f"Connection closed with tracker {addr[0]}:{addr[1]}")
    exit(0)


def print_help():
    print("Command list:")
    print("$> update [filename]\n -Report new file to your tracker.")
    print("$> delete [filename]\n -Report removed file to your tracker.")
    print("$> get [filename]\n -Get peer list of file.")
    print("$> getpeer\n -Get full peer list and print.")
    print("$> chat\n -Start chatting mode.")
    print("$> close\n -Close connection.")
    print("$> shutdown\n -Close connection and shutdown tracker.")


def __main__():
    serverIP = str(input("Please input tracker IP: "))
    serverPort = int(input("Please input tracker port: "))
    addr = (serverIP, serverPort)
    send_on(addr)
    t = threading.Thread(target=start_seed)
    t.setDaemon(True)
    t.start()
    hint = "Please input command, use 'help' to get help info:"
    while True:
        print(hint)
        raw = input('$> ')
        args = raw.split(' ')
        argnum = len(args) - 1
        command = args[0]
        if command == 'update' and argnum == 1:
            update_file(args[1], addr)
        elif command == 'delete' and argnum == 1:
            del_file(args[1], addr)
        elif command == 'get' and argnum == 1:
            finfo = get_finfo(args[1], addr)
            if finfo != None:
                recv_file(args[1], finfo)
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
