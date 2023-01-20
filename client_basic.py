import socket
import json

server_info = json.load(open('./client_ports_info.json'))
login_sock = socket.socket()  # 用于传递登录信息
login_sock.connect((server_info["server_IP"], server_info["server_port_login"]))   # 与服务器连接

# 用户登录
def login(nick_name):
    # 向服务器传递的用户信息
    client_login_info = dict()

    # 表示登录
    client_login_info["login"] = 1

    # 昵称
    client_login_info["nick_name"] = nick_name

    # 将用户登录信息转为json格式方便传输
    info = json.dumps(client_login_info)
    
    # 编码传输
    info = info.encode()
    
    # format格式化长度信息
    info_len = '{:<15}'.format(len(info))
    login_sock.send(info_len.encode())
    login_sock.send(info)

    # 接收服务器回复
    rep = receive_server()
    back = rep["return"]
    return back

# 用户接收服务器回复
def receive_server():
    rep = b''
    rep_size = 0

    # 接收服务器回复的长度,限制长度15
    rep_len = login_sock.recv(15).decode()

    # 去除回复长度的格式化,转为int
    rep_len = int(rep_len.strip())

    # 接收回复内容
    while rep_size < rep_len:
        # 允许多次接收,保证收到全部内容
        data = login_sock.recv(rep_len - rep_size)
        if not data:
            # 接收出错
            break
        rep += data
        rep_size += len(data)

    # 将json格式解码后转为python的数据格式
    rep = json.loads(rep.decode())
    return rep

# 用户退出
def exit():
    # 待办
    client_login_info = dict()      # 向服务器传递的用户信息
    client_login_info["login"] = 0  # 表示退出
    info = json.dumps(client_login_info)    # 将用户登录信息转为json格式方便传输
    info = info.encode()    # 编码传输
    info_len = '{:<15}'.format(len(info))  # format格式化长度信息
    login_sock.send(info_len.encode())
    login_sock.send(info)  # 发送info

    # 不需要接收服务器回复,直接退出
    login_sock.close()
