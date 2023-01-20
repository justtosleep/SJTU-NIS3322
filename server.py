import socket
from threading import Thread
import time
import json
import os

# 麻烦测试时注意改一下路径
PATH = r'D:\MTHfiles\contact\server_files'


class Server:
    def __init__(self):
        # 读取预定义的固定IP和复用端口
        server_info = json.load(open('./client_ports_info.json'))

        # 用于传递用户登录信息的套接字
        self.login_sock = socket.socket()

        # TCP端口复用, 赋值为1, 则表示生效
        self.login_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 绑定本机ip和登录端口
        self.login_sock.bind((server_info["server_IP"], server_info["server_port_login"]))

        # 最大用户数
        self.login_sock.listen(5)

        # 用于传递用户聊天信息的套接字
        self.chat_sock = socket.socket()
        self.chat_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.chat_sock.bind((server_info["server_IP"], server_info["server_port_chat"]))
        self.chat_sock.listen(5)

        # 用于传递用户文件信息的套接字
        self.file_sock = socket.socket()
        self.file_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.file_sock.bind((server_info["server_IP"], server_info["server_port_file"]))
        self.file_sock.listen(5)

        # 用户昵称与聊天套接字的绑定信息
        self.clients_name_chat = {}

        # 用户昵称与ip的绑定信息
        self.clients_name_ip = {}
        
        # 用户昵称与文件套接字的绑定信息
        self.clients_name_file = {}

        self.listen_connect()

    # 监听用户连接
    def listen_connect(self):
        # 循环监听,获取已连接用户信息
        while True:
            conn_login, addr_login = self.login_sock.accept()
            print(addr_login, "已连接登录端口")

            # 服务器启动多个线程处理多用户,一对一,防阻塞
            Thread(target=self.login, args=(conn_login, addr_login)).start()

    # 处理用户登录请求
    def login(self, conn_login, addr_login):
        try:
            # 循环接收请求
            while True:
                # 接收用户请求的长度,限制长度15
                req_len = conn_login.recv(15).decode()

                # 接收出错
                if not req_len:
                    break

                # 去除回复长度的格式化,转为int
                req_len = int(req_len.strip())

                # 接收请求的正文
                req = self.receive_client(req_len, conn_login)
                req = json.loads(req)

                # 根据请求的内容判断用户需求
                # 用户退出,释放资源,不做出回复
                if req["login"] == 0:
                    break

                # 用户登录
                elif req["login"] == 1:
                    # 验证昵称是否重复:重复登陆|重复昵称
                    reply = self.validate_name(req['nick_name'], addr_login)

                    # 将Python对象编码成json字符串
                    rep = json.dumps(reply)

                    # 向用户发送回复
                    rep = rep.encode()
                    rep_len = '{:<15}'.format(len(rep))
                    conn_login.send(rep_len.encode())
                    conn_login.send(rep)

                    if reply["return"] != 0:
                        # 返回值不为0，登录失败
                        pass
                    else:
                        # 登录成功
                        # 连接第二个聊天端口
                        conn_chat, addr_chat = self.chat_sock.accept()
                        print(addr_chat, "已连接聊天端口")
                        nick_name = reply['nick_name']

                        # 登记昵称和对应ip
                        self.clients_name_ip[nick_name] = addr_chat

                        # 登记昵称和对应用户套接字
                        self.clients_name_chat[nick_name] = conn_chat

                        # 启动多个线程处理多用户聊天
                        Thread(target=self.people_talk, args=(conn_chat, nick_name)).start()

                        # 启动线程处理用户文件
                        conn_file, addr_file = self.file_sock.accept()
                        print(addr_file, '已连接文件端口')
                        self.clients_name_file[nick_name] = conn_file
                        Thread(target=self.recv_file, args=(conn_file, nick_name)).start()

        except Exception as e:
            print(e)

        finally:
            conn_login.close()
            print(addr_login, '已关闭登录端口连接')

    # 验证昵称是否重复
    def validate_name(self, nick_name, addr_login):
        # 服务器回复
        rep = dict()

        # 保持统一,表示对登录请求的回复
        rep["login"] = 1

        # 当前所有登录用户的昵称
        nick_names = list(self.clients_name_ip.values())

        # 当前所有登录用户的ip
        addrs = list(self.clients_name_ip.keys())

        if nick_name in nick_names:
            if addr_login in addrs:
                # 重复登录
                rep["return"] = 1
            else:
                # 昵称重复
                rep["return"] = 2
        else:
            # 昵称可用,可以登录
            rep["return"] = 0
            rep['nick_name'] = nick_name
            print('{}登录成功'.format(nick_name))
        return rep

    # 接收用户信息
    @staticmethod
    def receive_client(req_len, conn_login):
        req = b''
        req_size = 0

        # 接收回复内容
        while req_size < req_len:
            # 允许多次接收,保证收到全部内容
            data = conn_login.recv(req_len - req_size)

            # 接收出错
            if not data:
                break
            req += data
            req_size += len(data)
        req = req.decode()
        return req

    # 关闭用户资源
    def close_client(self, nick_name):
        # 删除字典中昵称对应套接字,关闭套接字
        client = self.clients_name_chat.pop(nick_name)
        client.close()

        # 删除字典中昵称对应ip
        address = self.clients_name_ip.pop(nick_name)

        # 向服务器展示退出用户昵称和ip,提示相关套接字已关闭
        print(nick_name + str(address) + ' ', "已经离开,关闭聊天端口连接")

    # 用户初始化
    def people_talk(self, conn_chat, nick_name):

        # 欢迎用户上线
        self.hello_client(conn_chat, nick_name)

        # 发送在线用户名单,供用户初始化
        self.online_members()

        # 新用户上线提醒
        self.new_member(nick_name)

        try:
            # 循环监听用户消息
            while True:
                # 接收用户消息长度
                message_len = conn_chat.recv(15).decode()
                if not message_len:
                    break
                message_len = int(message_len.strip())

                # 接收用户消息正文
                message = self.receive_client(message_len, conn_chat)

                # 用户退出,退出try进入finally进行处理
                if 'login' in message:
                    break

                # 私聊
                elif 'solo_content' in message:
                    message = json.loads(message)
                    other_nickname = message['solo_nickname']
                    content = message['solo_content']
                    if other_nickname != nick_name:
                        # 接收邀请聊天消息并转发
                        Thread(target=self.solo_chat, args=(other_nickname, nick_name, content)).start()

                # 私聊表情
                elif 'solo_emoji' in message:
                    message = json.loads(message)
                    other_nickname = message['solo_nickname']
                    content = message['solo_emoji']
                    if other_nickname != nick_name:
                        # 接收邀请聊天消息并转发
                        Thread(target=self.solo_emoji, args=(other_nickname, nick_name, content)).start()

                # 公共聊天发送表情
                elif 'emoji' in message:
                    message = json.loads(message)
                    nick_data = nick_name + " " + time.strftime("%x") + ':\n'
                    rep = {'emoji': message['emoji'], 'nick_data': nick_data}
                    rep = json.dumps(rep)
                    rep = rep.encode()
                    rep_len = '{:<15}'.format(len(rep))

                    # 将消息群发给聊天室所有用户(除发送者)
                    self.sendall_part(nick_name, rep, rep_len)

                # 公聊
                else:
                    recv_data = nick_name + " " + time.strftime("%x") + ':\n' + message + '\n'
                    recv_data = recv_data.encode()
                    recv_data_len = '{:<15}'.format(len(recv_data))

                    # 将消息群发给聊天室所有用户(除发送者)
                    self.sendall_part(nick_name, recv_data, recv_data_len)

        except Exception as e:
            print(e)
        finally:
            # 用户下线,释放资源
            self.close_client(nick_name)

            # 重新更新在线人数
            self.online_members()

            # 用户昵称和退出消息
            quit_client = {'quit_member': nick_name}
            quit_client = json.dumps(quit_client, ensure_ascii=False)
            quit_client = quit_client.encode()
            quit_client_len = '{:<15}'.format(len(quit_client))

            # 向所有用户展示退出用户
            self.sendall(quit_client, quit_client_len)

    # 接收文件
    def recv_file(self, conn_file, nick_name):
        try:
            # 循环监听用户消息
            while True:
                # 接收用户消息长度
                message_len = conn_file.recv(15).decode()
                if not message_len:
                    break
                message_len = int(message_len.strip())

                # 接收用户消息正文
                message = self.receive_client(message_len, conn_file)

                # 接收用户文件
                if 'file_send' in message:
                    message = json.loads(message)
                    user = message['nickname']
                    filename = os.path.basename(message['filename'])
                    file_path = os.path.join(PATH, filename)
                    file_size = message['file_size']
                    try:
                        with open(file_path, "wb") as f:
                            for _ in range(file_size):
                                # 从客户端读取数据
                                bytes_read = conn_file.recv(4096)

                                # 没有数据传输
                                if not bytes_read:
                                    break

                                # 读取写入
                                f.write(bytes_read)
                    except Exception as e:
                        print(e)

                    reply = {'filename': filename, 'file_size': file_size, 'nickname': nick_name}
                    # 将Python对象编码成json字符串
                    rep = json.dumps(reply)

                    # 向用户发送文件传输请求
                    rep = rep.encode()
                    rep_len = '{:<15}'.format(len(rep))
                    sock = self.clients_name_chat[user]
                    sock.send(rep_len.encode())
                    sock.send(rep)

                # 向用户发送文件
                elif 'file_recv' in message:
                    message = json.loads(message)
                    filename = os.path.basename(message['filename'])
                    file_path = os.path.join(PATH, filename)
                    print(file_path)
                    file_size = message['file_size']
                    try:
                        size = 0
                        with open(file_path, "rb") as f:
                            for _ in range(file_size):
                                if size >= file_size:
                                    break
                                # 读取文件
                                bytes_read = f.read(4096)

                                if not bytes_read:
                                    break

                                # sendall确保即使网络忙碌，数据仍然可以传输
                                conn_file.sendall(bytes_read)

                                size += len(bytes_read)

                    except Exception as e:
                        print(e)
                    finally:
                        break

        except Exception as e:
            print(e)
        finally:
            # 删除字典中昵称对应套接字,关闭套接字
            client = self.clients_name_file.pop(nick_name)
            client.close()
            print(nick_name + "关闭文件端口连接")

    # 发送在线成员名单,供用户初始化
    def online_members(self):
        # 提取在线用户昵称
        clients_nickname = list(self.clients_name_chat.keys())

        online_clients = {'online_members': clients_nickname}
        online_clients = json.dumps(online_clients, ensure_ascii=False)
        online_clients = online_clients.encode()
        online_clients_len = '{:<15}'.format(len(online_clients))

        # 向所有用户群发名单,更新名单
        self.sendall(online_clients, online_clients_len)

    # 处理群发请求
    def sendall(self, content, content_len):
        # 提取所有在线用户的套接字
        for conn in self.clients_name_chat.values():
            try:
                conn.send(content_len.encode())
                conn.send(content)
            except Exception as e:
                print(e)

    # 处理部分群发请求
    def sendall_part(self, nickname, content, content_len):
        # 提取所有在线用户的套接字
        for name in self.clients_name_chat.keys():
            if name != nickname:
                conn = self.clients_name_chat[name]
                try:
                    conn.send(content_len.encode())
                    conn.send(content)
                except Exception as e:
                    print(e)

    # 新用户上线提醒
    def new_member(self, nick_name):
        new_client = {'new_member': nick_name}
        new_client = json.dumps(new_client, ensure_ascii=False)
        new_client = new_client.encode()
        new_client_len = '{:<15}'.format(len(new_client))

        # 向所有用户群发上线提醒
        self.sendall(new_client, new_client_len)

    # 处理私聊请求,转发消息给私聊对象
    def solo_emoji(self, other_nickname, nick_name, content):
        # 找到私聊对象的套接字
        other_sock = self.clients_name_chat[other_nickname]

        try:
            # 私聊消息昵称改为发起私聊的用户昵称
            other_req = {'solo_nickname': nick_name, 'solo_emoji': content}

            # 转发消息给私聊对象
            other_req = json.dumps(other_req)
            other_req = other_req.encode()
            other_req_len = '{:<15}'.format(len(other_req))
            other_sock.send(other_req_len.encode())
            other_sock.send(other_req)
        except Exception as e:
            print(e)

    # 处理私聊请求,转发消息给私聊对象
    def solo_chat(self, other_nickname, nick_name, content):
        # 找到私聊对象的套接字
        other_sock = self.clients_name_chat[other_nickname]

        try:
            # 私聊消息昵称改为发起私聊的用户昵称
            other_req = {'solo_nickname': nick_name, 'solo_content': content}

            # 转发消息给私聊对象,消息可能包含汉字,不能用ascii表示
            other_req = json.dumps(other_req, ensure_ascii=False)
            other_req = other_req.encode()
            other_req_len = '{:<15}'.format(len(other_req))
            other_sock.send(other_req_len.encode())
            other_sock.send(other_req)
        except Exception as e:
            print(e)

    # 向用户发送欢迎上线的消息
    @staticmethod
    def hello_client(conn_chat, nick_name):
        # 发送用户昵称,向用户确认
        hello_content = {'hello_client': nick_name}
        hello_content = json.dumps(hello_content, ensure_ascii=False)
        hello_content = hello_content.encode()
        hello_content_len = '{:<15}'.format(len(hello_content))
        try:
            conn_chat.send(hello_content_len.encode())
            conn_chat.send(hello_content)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    Server()
