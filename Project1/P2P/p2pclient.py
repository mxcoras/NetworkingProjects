"""P2P通信客户端"""

from socket import *
import struct
import threading
import json


clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.settimeout(60)
inSocket = socket(AF_INET, SOCK_DGRAM)
inSocket.bind(('', 12000))
