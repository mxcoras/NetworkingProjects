# P2P
[TOF]
## 概况
- P2P程序设计中，分为**Tracker**、**Client**两大部分。
- p2pclient.py运行在客户端上，使用时连接Tracker服务器，进行文件下载
- tracker.py长期运行在单独的机器上，起信息交互、日志记录的作用。
- 本程序基于自实现协议，采用多线程管理的技术，结合TCP、UDP的传输策略实现了多种功能，除文件下载之外还实现了各客户端之间的聊天功能。

## 设计与实现
- 接下来将介绍以下三个功能的设计思想与代码实现:
    - **文件传输**
    - **聊天功能**
    - **日志记录**
    - 关闭服务器
- 本程序中，无论是Tracker与Client还是Client与Client之间的通信都遵从以下规则，分为**头部**与**数据**两个部分
    - 头部:由一个char+一个/两个int组成。char表示client/server的状态或操作，int表示分组的总长度,或获取文件块的编号。
        - ***Peer->Tracker***
            - O:上线
            - F:下线
            - X:停止对某文件做种
            - D:开始对某文件做种
            - P:获取peers信息
            - G:请求下载文件
            - A:确认信息
        - ***Peer->Peer***
            - S:开始传输文件
            - E:传输错误
            - T:传输完毕
            - A:ACK，用于确认每个分组是否正确传输
            - I:正在传输
            - G:请求文件
            - M:开始聊天
        - ***Tracker->Peers***
            - N:表示否定/文件不存在/失败等情况
            - Y:表示肯定/成功等情况
            - F:传输文件信息
            - P:传输peers信息
    - 数据:按需传递不同类型的消息。

### 文件传输
#### peers管理
- TCP协议
- 使用json格式保存文件、peers信息
- Tracker程序运行后，tracker端多线程调用tcp_accept函数接受client连入。
```Python
# -----------Tracker端-----------
# Tracker端建立套接字
t = threading.Thread(target=tcp_accept)
t.setDaemon(True)
t.start()
thread_list.append(t)
# 加入线程池
newSocket, addr = serverSocket.accept()
在tcp_accept函数中建立套接字

``` 

- Tracker端使用tcp_connect程序监听套接字，根据client端发送的头部判断进行不同的操作。

- Client程序调用send_on函数连接Tracker服务器，向tracker汇报信息。tracker接收到传入后，调用peer_on函数，记录Client上线。

```Python
    try:
        clientSocket.connect(addr)
        body = str(CHAT_PORT).encode()
        plen = len(body) + 5
        clientSocket.send(struct.pack("!cI", b'O', plen) + body)
        thr_error(recv_data()[0], b'Y', addr)
    except:
        conn_fail(addr)
    print(f"Successfully connect to {addr[0]}:{addr[1]}.")
```

- Client端调用update_file/del_file函数向tracker提交/删除文件信息。
    - **提交**
    - 首先根据文件名，检测该文件是否存在
    - 若存在，发送文件名、文件大小、下载端口到Tracker
    - **删除**
    - 直接发送头部为X、正文为文件名的数据包至Tracker

- Tracker端收到请求后，调用update_flist/del_flist对文件列表/peers列表进行修改

```python
def del_flist(psocket, addr, body=None, all=False):
    # 根据参数all判断，是完全删除还是部分删除
    if all == True:
        for filename in list(fileList.keys()):
            try:
                with flock:
                    plist = fileList[filename]["peers"]
                    for i in range(len(plist)):
                        if plist[i][0] == addr[0]:
                            del plist[i]
            except:
                log = f"Delete fileinfo of {addr} failed."
                logger(log, level='Error')
    # 若peers数为0，删除该文件记录
            if len(fileList[filename]["peers"]) == 0:
                with flock:
                    del fileList[filename]
    else:
        if not body:
            send_no(psocket, addr)
            return
        filename = body
        if filename not in fileList:
            send_no(psocket, addr)
            return
        try:
        # 删除单个记录
            with flock:
                plist = fileList[filename]["peers"]
                for i in range(len(plist)):
                    if plist[i][0] == addr[0]:
                        del plist[i]
        except:
            send_no(psocket, addr)
            log = f"Delete fileinfo of {addr} failed."
            logger(log, level='Error')
            return
        # 再次判断peer数量
        if len(fileList[filename]["peers"]) == 0:
            with flock:
                del fileList[filename]
        # 以下省略
```

- Client通过get_peers/get_finfo向Tracker获取文件/peer信息。

- Tracker收到请求后，调用ret_flist/ret_plist解析peers列表与文件列表的json文件，发送至Client。

- Client通过返回的信息，调用recv_file函数向peers请求下载文件
```python
def recv_file(filename, finfo: dict):
    #首先获取peers列表
    peers = finfo.get("peers", [])
    #若peers为1，调用recv_from_peers向该单独的peers请求下载文件
    if len(peers) == 1:
        recv_from_peers(tuple(peers[0]), filename, 0)
    #若peers为2，建立多线程下载两部分文件
    elif len(peers) == 2:
        for i in range(2):
            t = threading.Thread(target=recv_from_peers, args=(tuple(peers[i]), filename, i+1))
            t.setDaemon(True)
            t.start()
            thread_list.append(t)
        #将两个线程下载得到的文件合并
        for j in thread_list:
            j.join()
        part1 = open(filename + '.1', 'rb')
        part2 = open(filename + '.2', 'rb')
        with open(filename, 'wb') as f:
            f.write(part1.read())
            f.write(part2.read())
        part1.close()
        #删除临时文件
        remove(filename + '.1')
        part2.close()
        remove(filename + '.2')
    print(f"Successful download {filename}")
```

- peers使用start_seed函数监听做种，当收到下载文件的请求时，调用send_file函数处理下载请求。

```python
def send_file(peerAddr, filename, part):
    try:
    # 尝试打开文件
        open(filename, 'rb')
    except IOError:
        seedSocket.sendto(struct.pack("!cII", b'E', 0, 9), peerAddr)
        return
    # 根据接收到的part信息进行分块传输
    with open(filename, 'rb') as f:
        data = f.read()
        size = len(data)
        bodybytes = b''
        f.seek(0)
    # 若part为0，则传输整个文件
        if part == 0:
            bodybytes = f.read()
    # 若part为1/2，则传输前半部或后半部
        elif part == 1:
            bodybytes = f.read(int(size/2))
        elif part == 2:
            f.read(int(size/2))
            bodybytes = f.read()
    seedSocket.sendto(struct.pack("!cII", b'S', 0, 9), peerAddr)
    # 若接收不到ACK，传输失败，结束传输
    if not recv_ack(peerAddr, 0):
        return
    fix = randint(1, 1000)
    with open('TEMP.'+str(fix), 'wb+') as sf:
        sf.write(bodybytes)
        sf.seek(0)
        packnum = 1
    # 分块传输数据包
        while True:
            body = sf.read(10231)
            if not body:
                seedSocket.sendto(struct.pack("!cII", b'T', 0, 9), peerAddr)
                print(f"Send {filename} to {peerAddr} complete.\n>$ ", end='')
                if not recv_ack(peerAddr, 0):
                    print("[Warning] Complete ACK not recieved.")
                sf.close()
                remove('TEMP.'+str(fix))
                return
            bodySize = len(body) + 9
            package = struct.pack("!cII", b'I', packnum, bodySize) + body
            seedSocket.sendto(package, peerAddr)
    # 若接收不到ACK，传输失败，结束传输
            if not recv_ack(peerAddr, packnum):
                print("OOS")
                sf.close()
                remove('TEMP.'+str(fix))
                return
            packnum += 1
    sf.close()
    remove('TEMP.'+str(fix))
```
### 聊天功能
- client方面调用start_chat函数，多线程调用recv_msg函数接受聊天请求传入，同时按照用户键入地址，与另一用户建立联系。

```python
def start_chat():
# ----节选---
    while True:
    # 建立连接后，发送聊天信息
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
        # recvfrom函数阻塞监听聊天信息传入
            package, serverAddr = chatSocket.recvfrom(2048)
        except:
            print("[Warning]: Chat socket closed.")
            return
        #解码并呈现信息
        msgBody = package[9:].decode()
        print(
            f"\nMessage from {serverAddr[0]}:{serverAddr[1]}: \n{msgBody}\n\nPlease input message, or '!q' to exit: ")
```
### 日志记录
- 在tracker端，tracker、client进行每个操作时都调用logger函数向logs组记录日志。如下例：
```
[Info][2020-06-03 21:15:20] The server is online.
[Info][2020-06-03 21:15:38] Connection from *.*.*.*:*. 
```

## 使用方法
- 需要Python 3.6及以上环境
- 在物理机或虚拟机上打开tracker.py，进入以下模拟终端界面：
```
The server is online.

Please use 'cat' to read all logs, 'cat [num]' to read [nums] lines of latest logs.
Type 'exitnow' to exit.
$>
```
- 此时tracker服务器已成功上线，若想获取文件或peers列表可输入flist/plist，输入cat展示服务器日志，输入exitnow可关闭服务器

- 在多个客户端中打开p2pclient.py，按照提示输入服务器ip与端口号后收到以下提示：
```
Please input tracker IP: *.*.*.*
Please input tracker port: *
Successfully connect to *.*.*.*:*
Please input command, use 'help' to get help info:
$>
```
- 此时输入help，可获得命令解释：
```
$> help
Command list:
# 提交文件信息
$> update [filename]
 -Report new file to your tracker.
# 删除做种信息
$> delete [filename]
 -Report removed file to your tracker.
# 下载文件
$> get [filename]
 -Get peer list of file.
# 获取做种列表
$> getpeer
 -Get full peer list and print.
# 开始聊天
$> chat
 -Start chatting mode.
# 关闭本机进程
$> close
 -Close connection.
# 关闭tracker进程
$> shutdown
 -Close connection and shutdown tracker.
Please input command, use 'help' to get help info:
```

## 版本

**2020.6.23**: 所有功能均通过测试，完美可用。