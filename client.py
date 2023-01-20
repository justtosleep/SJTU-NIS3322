from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import re
import socket
import json
import time
import os

import client_basic

from client_login_form import Ui_MainWindow_login
from client_chat_form import Ui_MainWindow_chat
from client_talk_form import Ui_MainWindow_talk
from client_file_form import Ui_MainWindow_file
from client_recvfile_form import Ui_MainWindow_recvfile
from client_emoji_form import Ui_MainWindow_emoji

server_info = json.load(open('./client_ports_info.json'))


# 登录界面
class Client_Login(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow_login()
        self.ui.setupUi(self)

        # 隐藏外部窗口
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 按下"登录"键则尝试登录
        self.ui.pushButton_login.clicked.connect(self.login)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True

            # 获取鼠标相对窗口的位置
            self.m_Position = event.globalPos() - self.pos()
            event.accept()

            # 更改鼠标图标
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

    def mouseMoveEvent(self, mouse_Event):
        if QtCore.Qt.LeftButton and self.m_flag:
            # 更改窗口位置
            self.move(mouse_Event.globalPos() - self.m_Position)
            mouse_Event.accept()

    def mouseReleaseEvent(self, mouse_Event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    # 按下enter键也可以登录
    def keyPressEvent(self, e):
        # 大键盘enter
        if e.key() == Qt.Key_Return:
            self.login()

        # 小键盘enter
        elif e.key() == Qt.Key_Enter:
            self.login()

    # 用户登录
    def login(self):
        # 消息盒子
        box = QMessageBox()

        # 接收用户输入的昵称
        nick_name = self.ui.lineEdit_nickname.text()

        # 若昵称不为空
        if nick_name:
            # 利用正则式判断昵称是否合法
            # 正则式规则:用户名长1~9位,只能有大小写字母/数字/下划线
            if not re.match("^[a-zA-Z0-9_]{0,8}$", nick_name):
                # 对于非法用户名弹窗提醒
                box.warning(self, "提示", "昵称输入格式有误!")
            else:
                try:
                    # 将昵称信息发给服务器,根据回复确认昵称是否可用
                    a = client_basic.login(nick_name)

                    # 昵称可用
                    if a == 0:
                        # 创建聊天界面
                        self.client = Client_Chat()

                        # 打开聊天界面
                        self.client.show()

                        # 关闭登录界面
                        self.close()
                    elif a == 1:
                        # 弹窗提醒已经登录
                        box.warning(self, "提示", "您已登录，无需重复登录！")
                    elif a == 2:
                        # 弹窗提醒昵称重复
                        box.warning(self, "提示", "昵称重复!")
                except Exception as e:
                    print(e)
        # 对于非法用户名弹窗提醒
        else:
            box.warning(self, "提示", "昵称不能为空!")

    # 用户退出
    def exit(self):
        self.close()
        client_basic.exit()


# 聊天界面
class Client_Chat(QMainWindow):
    members = []
    solo_talk = []

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow_chat()
        self.ui.setupUi(self)

        # 隐藏外部窗口
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 放大窗口按钮
        self.ui.pushButton_max.clicked.connect(self.restore_or_maximize_window)

        # 发送消息按钮
        self.ui.pushButton_send.clicked.connect(self.send_msg)

        # 表情按钮
        self.ui.pushButton_emoji.clicked.connect(self.emoji)

        # 用户列表点击开启私聊
        self.ui.listWidget_members.itemClicked['QListWidgetItem*'].connect(self.click_solo)

        # 开启线程处理任务
        self.work_thread()

    # 匿名类，线程处理
    def work_thread(self):
        # 创建线程接收消息
        self.thread_chat = Thread_chat()

        # 信号返回数据则进入槽函数
        self.thread_chat.signal.connect(self.chat_solver)

        # 开启线程
        self.thread_chat.start()

    # 接收消息
    def chat_solver(self, rep):
        try:
            # 服务器发来欢迎消息
            if 'hello_client' in rep:
                rep = json.loads(rep)
                nickname = rep['hello_client']
                my_name = nickname + '(我)'
                self.my_nickname = my_name
                self.members.append(nickname)
                self.ui.listWidget_members.addItem(my_name)

            # 服务器发来在线用户名单列表
            elif 'online_members' in rep:
                rep = json.loads(rep)

                # 提取用户名单
                clients_nickname = rep['online_members']

                # 展示在线用户数量
                members_info = '在线用户:' + str(len(clients_nickname)) + '人'
                self.ui.label_mebers.setText(members_info)

                # 更新本地在线用户名单
                for i, n in enumerate(clients_nickname):
                    # 有新用户
                    if n not in self.members:
                        # 将用户名加入在线名单
                        self.ui.listWidget_members.addItem(n)

                        # 将用户名加入类的用户名列表,并开启私聊功能,记录私聊窗口
                        Client_Chat.members.append(n)
                        n_talk = Client_Talk(self.thread_chat)
                        Client_Chat.solo_talk.append([n_talk, n, 0])

            # 私聊消息
            elif 'solo_content' in rep:
                # 提取昵称和消息正文
                solo_content = json.loads(rep)
                nick_name = solo_content['solo_nickname']
                content = solo_content['solo_content']
                contents = nick_name + " " + time.strftime("%x") + ':\n' + content + '\n'

                # 找到对方私聊窗口
                for k in Client_Chat.solo_talk:
                    if nick_name == k[1]:
                        # 窗口已经打开,直接更新消息
                        if k[2] == 1:
                            k[0].ui.textBrowser_talk.append(contents)

                        # 窗口未打开
                        else:
                            # 打开窗口
                            k[2] = 1
                            k[0].show()
                            k[0].ui.label_nickname.setText(nick_name)
                            k[0].ui.textBrowser_talk.append(contents)

            # 私聊表情
            elif 'solo_emoji' in rep:
                # 提取昵称和表情
                solo_content = json.loads(rep)
                nick_name = solo_content['solo_nickname']
                content = solo_content['solo_emoji']
                contents = nick_name + " " + time.strftime("%x") + ':\n'

                # 表情路径
                path = "<img src=\"./img/emoji/emoji (%d).png\"/>" % content

                # 找到对方私聊窗口
                for k in Client_Chat.solo_talk:
                    if nick_name == k[1]:
                        # 窗口已经打开,直接更新消息
                        if k[2] == 1:
                            k[0].ui.textBrowser_talk.append(contents)
                            k[0].ui.textBrowser_talk.insertHtml(path)

                        # 窗口未打开
                        else:
                            # 打开窗口
                            k[2] = 1
                            k[0].show()
                            k[0].ui.label_nickname.setText(nick_name)
                            k[0].ui.textBrowser_talk.append(contents)
                            k[0].ui.textBrowser_talk.insertHtml(path)

            # 文件
            elif 'filename' in rep:
                file_info = json.loads(rep)
                self.recvfile = Client_Recvfile(file_info)
                self.recvfile.show()

            # 欢迎新用户
            elif 'new_member' in rep:
                new_member = json.loads(rep)
                nickname = new_member['new_member']
                welcome = '--------欢迎' + nickname + '上线--------'
                self.ui.textBrowser_chat.append(welcome)

            # 有用户退出
            elif 'quit_member' in rep:
                quit_member = json.loads(rep)
                nickname = quit_member['quit_member']
                goodbye = '--------' + nickname + '已经离开--------'
                self.ui.textBrowser_chat.append(goodbye)

                # 从本地用户列表删除该用户
                item = self.ui.listWidget_members.findItems(nickname, Qt.MatchExactly)[0]
                row = self.ui.listWidget_members.row(item)
                self.ui.listWidget_members.takeItem(row)

            # 表情
            elif 'emoji' in rep:
                rep = json.loads(rep)
                self.ui.textBrowser_chat.append(rep['nick_data'])
                item = rep['emoji']

                # 表情路径
                path = "<img src=\"./img/emoji/emoji (%d).png\"/>" % item
                self.ui.textBrowser_chat.insertHtml(path)

            # 普通消息
            else:
                self.ui.textBrowser_chat.append(rep)

        except Exception as f:
            print(f)

    # 发送消息
    def send_msg(self):
        try:
            req = self.ui.textEdit_message.toPlainText()
            if req:
                reqs = '我' + " " + time.strftime("%x") + ':\n' + req + '\n'
                self.ui.textBrowser_chat.append(reqs)
                self.ui.textEdit_message.clear()
                self.thread_chat.send_server(req)
        except Exception as e:
            print(e)

    # 点击用户列表聊天
    def click_solo(self, e):
        try:
            box = QtWidgets.QMessageBox()

            # 被点击用户
            name = e.text()

            # 点击用户自己无效
            if name != self.my_nickname:
                for k in Client_Chat.solo_talk:
                    if name == k[1]:
                        # 窗口已经打开
                        if k[2] == 1:
                            box.information(self, "提示", "不能重复开启聊天窗口")
                        # 窗口未打开
                        else:
                            k[0].show()
                            k[0].ui.textBrowser_talk.clear()
                            k[0].ui.label_nickname.setText(name)
                            k[2] = 1
                        break

        except Exception as f:
            print(f)

    # 表情
    def emoji(self):
        self.emoji = Client_Emoji()
        self.emoji.show()
        self.emoji.signal.connect(self.send_emoji)

    # 发送表情
    def send_emoji(self):
        row, col = self.emoji.res()
        col += 1

        # 用户使用的表情
        item = row * 5 + col

        # 表情路径
        path = "<img src=\"./img/emoji/emoji (%d).png\"/>" % item
        reqs = '我' + " " + time.strftime("%x") + ':\n'
        self.ui.textBrowser_chat.append(reqs)
        self.ui.textBrowser_chat.insertHtml(path)

        # 发给服务器
        emoji = {'emoji': item}
        emoji = json.dumps(emoji)
        self.thread_chat.send_server(emoji)

    # 放大缩小
    def restore_or_maximize_window(self):
        if self.isMaximized():
            self.showNormal()
            self.ui.pushButton_max.setIcon(QtGui.QIcon(u":/icon/img/icon/maxsize.png"))
        else:
            self.showMaximized()
            self.ui.pushButton_max.setIcon(QtGui.QIcon(u":/icon/img/icon/minimizeWhite.png"))

    # 拖拽窗口
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True

            # 获取鼠标相对窗口的位置
            self.m_Position = event.globalPos() - self.pos()
            event.accept()

            # 更改鼠标图标
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

    def mouseMoveEvent(self, mouse_Event):
        if QtCore.Qt.LeftButton and self.m_flag:
            # 更改窗口位置
            self.move(mouse_Event.globalPos() - self.m_Position)
            mouse_Event.accept()

    def mouseReleaseEvent(self, mouse_Event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


# 私聊
class Client_Talk(QMainWindow):
    # 获取当前路径
    cwd = os.getcwd()
    nickname = ''
    file = ''

    def __init__(self, thread_chat):
        super().__init__()
        self.ui = Ui_MainWindow_talk()
        self.ui.setupUi(self)
        self.thread_chat = thread_chat

        # 隐藏外部窗口
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 发送消息按钮
        self.ui.pushButton_send.clicked.connect(self.send_content)

        # 发送消息按钮
        self.ui.pushButton_send.clicked.connect(self.send_content)

        # 关闭按钮
        self.ui.pushButton_close.clicked.connect(self.closed)

        # 发送文件按钮
        self.ui.pushButton_files.clicked.connect(self.send_file)

        # 发送表情按钮
        self.ui.pushButton_emoji.clicked.connect(self.emoji)

    # 收到私聊消息
    def receive_content(self, contents):
        contents = self.ui.label_nickname.text() + " " + time.strftime("%x") + ':\n' + contents + '\n'
        self.ui.textBrowser_talk.append(contents)

    # 关闭私聊窗口
    def closed(self):
        try:
            nickname = self.ui.label_nickname.text()
            self.close()

            # 将私聊窗口标记为关闭
            for k in Client_Chat.solo_talk:
                if nickname == k[1]:
                    k[2] = 0
        except Exception as e:
            print(e)

    # 发送私聊消息
    def send_content(self):
        try:
            content = self.ui.textEdit_message.toPlainText()

            # 空消息不发送
            if content != '':
                self.ui.textEdit_message.clear()
                contents = '我' + " " + time.strftime("%x") + ':\n' + content + '\n'
                self.ui.textBrowser_talk.append(contents)

                # 服务器转发消息
                solo_content = dict()
                self.nickname = self.ui.label_nickname.text()
                solo_content['solo_nickname'] = self.nickname
                solo_content['solo_content'] = content
                cont = json.dumps(solo_content, ensure_ascii=False)

                # 由线程负责发送消息给服务器
                self.thread_chat.send_server(cont)
        except Exception as e:
            print(e)

    # 表情
    def emoji(self):
        self.emoji = Client_Emoji()
        self.emoji.show()
        self.emoji.signal.connect(self.send_emoji)

    # 发送私聊表情
    def send_emoji(self):
        row, col = self.emoji.res()
        col += 1

        # 用户使用的表情
        item = row * 5 + col
        try:
            # 表情路径
            path = "<img src=\"./img/emoji/emoji (%d).png\"/>" % item
            reqs = '我' + " " + time.strftime("%x") + ':\n'
            self.ui.textBrowser_talk.append(reqs)
            self.ui.textBrowser_talk.insertHtml(path)

            # 发给服务器
            self.nickname = self.ui.label_nickname.text()
            emoji = {'solo_nickname': self.nickname, 'solo_emoji': item}
            emoji = json.dumps(emoji)
            # 由线程负责发送消息给服务器
            self.thread_chat.send_server(emoji)
        except Exception as e:
            print(e)

    # 发送文件
    def send_file(self):
        self.nickname = self.ui.label_nickname.text()

        # self.cwd:起始路径
        # "All Files (*);;Text Files (*.txt)":设置文件扩展名过滤,用双分号间隔
        filename, filetype = QFileDialog.getOpenFileName(self, "选取文件", self.cwd,
                                                         "All Files (*);;Text Files (*.txt)")
        if filename == "":
            print("\n取消选择")
            return
        print("\n你选择的文件为:")
        print(filename)

        # 打开发送文件进度条
        self.file = Client_File(self.nickname, filename, filetype)
        self.file.show()

    # 拖拽窗口
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True

            # 获取鼠标相对窗口的位置
            self.m_Position = event.globalPos() - self.pos()
            event.accept()

            # 更改鼠标图标
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

    def mouseMoveEvent(self, mouse_Event):
        if QtCore.Qt.LeftButton and self.m_flag:
            # 更改窗口位置
            self.move(mouse_Event.globalPos() - self.m_Position)
            mouse_Event.accept()

    def mouseReleaseEvent(self, mouse_Event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


# 发送文件
class Client_File(QMainWindow):
    # 用于传递文件信息的套接字
    file_sock = socket.socket()

    def __init__(self, nickname, filename, filetype):
        super().__init__()
        self.ui = Ui_MainWindow_file()
        self.ui.setupUi(self)
        self.nickname = nickname
        self.filename = filename
        self.filetype = filetype

        # 隐藏外部窗口
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 连接客户端的文件端口
        self.file_sock.connect((server_info["server_IP"], server_info["server_port_file"]))
        print('连接到文件端口')

        self.send_file()

    # 向服务器发送指定文件
    def send_file(self):
        # 文件大小
        file_size = os.path.getsize(self.filename)
        file_info = {'file_send': 1, 'filename': self.filename, 'file_size': file_size, 'nickname': self.nickname}
        file_info = json.dumps(file_info)
        self.send_server(file_info)

        # 实际传输大小
        size = 0
        try:
            # 文件传输
            with open(self.filename, "rb") as f:
                for _ in range(file_size):
                    # 读取文件
                    bytes_read = f.read(4096)

                    if not bytes_read:
                        break

                    # sendall确保即使网络忙碌，数据仍然可以传输
                    self.file_sock.sendall(bytes_read)

                    # 更新传输进度条
                    size += len(bytes_read)
                    self.ui.progressBar.setValue(int(size / file_size * 100))
        except Exception as e:
            print(e)
        finally:
            self.close()
            self.file_sock.close()
            print("断开文件端口连接")

    # 发送消息
    def send_server(self, mes):
        mes = mes.encode()
        mes_len = '{:<15}'.format(len(mes))
        self.file_sock.send(mes_len.encode())
        self.file_sock.send(mes)

    # 拖拽窗口
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True

            # 获取鼠标相对窗口的位置
            self.m_Position = event.globalPos() - self.pos()
            event.accept()

            # 更改鼠标图标
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

    def mouseMoveEvent(self, mouse_Event):
        if QtCore.Qt.LeftButton and self.m_flag:
            # 更改窗口位置
            self.move(mouse_Event.globalPos() - self.m_Position)
            mouse_Event.accept()

    def mouseReleaseEvent(self, mouse_Event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


# 接收文件
class Client_Recvfile(QMainWindow):
    # 获取当前路径
    cwd = os.getcwd()

    # 用于传递文件信息的套接字
    file_sock = socket.socket()

    def __init__(self, file_info):
        super().__init__()
        self.ui = Ui_MainWindow_recvfile()
        self.ui.setupUi(self)
        self.filename = file_info['filename']
        self.file_size = file_info['file_size']
        self.nickname = file_info['nickname']
        self.ui.label_nickname.setText(self.nickname)

        # 隐藏外部窗口
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 接收按钮
        self.ui.pushButton_recv.clicked.connect(self.recv)

        # 拒绝按钮
        self.ui.pushButton_refu.clicked.connect(self.refu)

        # 连接客户端的文件端口
        self.file_sock.connect((server_info["server_IP"], server_info["server_port_file"]))
        print('连接到文件端口')

    def recv(self):
        while 1:
            box = QtWidgets.QMessageBox()
            # 选择保存文件夹
            self.dir = QFileDialog.getExistingDirectory(self, "选取文件夹", self.cwd)
            if self.dir == "":
                box.warning(self, '提示', '您还没有选择保存位置!')
            else:
                print("\n你选择的文件夹为:")
                print(self.dir)
                break

        # 提示服务器可以发文件
        req = {'file_recv': 1, 'filename': self.filename, 'file_size': self.file_size}
        req = json.dumps(req, ensure_ascii=False)
        req = req.encode()
        req_len = '{:<15}'.format(len(req))
        self.file_sock.send(req_len.encode())
        self.file_sock.send(req)

        # 准备保存文件
        self.save()

    def refu(self):
        self.closed()

    def closed(self):
        self.close()
        self.file_sock.close()
        print("断开文件端口连接")

    def save(self):
        filename = os.path.basename(self.filename)
        save_path = os.path.join(self.dir, filename)
        # 实际传输大小
        size = 0
        try:
            with open(save_path, "wb") as f:
                for _ in range(self.file_size):
                    # 从服务器读取数据
                    bytes_read = self.file_sock.recv(4096)

                    # 没有数据传输
                    if not bytes_read:
                        break

                    # 读取写入
                    f.write(bytes_read)

                    # 更新传输进度条
                    size += len(bytes_read)
                    self.ui.progressBar.setValue(int(size / self.file_size * 100))

        except Exception as f:
            print(f)
        finally:
            self.closed()

    # 拖拽窗口
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True

            # 获取鼠标相对窗口的位置
            self.m_Position = event.globalPos() - self.pos()
            event.accept()

            # 更改鼠标图标
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

    def mouseMoveEvent(self, mouse_Event):
        if QtCore.Qt.LeftButton and self.m_flag:
            # 更改窗口位置
            self.move(mouse_Event.globalPos() - self.m_Position)
            mouse_Event.accept()

    def mouseReleaseEvent(self, mouse_Event):
        self.m_flag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


# 表情
class Client_Emoji(QMainWindow):
    # 设置自定义信号,传递字符串数据
    signal = pyqtSignal(int)

    def __init__(self, ):
        super().__init__()
        self.ui = Ui_MainWindow_emoji()
        self.ui.setupUi(self)

        # 隐藏外部窗口
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 初始化所有表情
        self.init_em()

        # 点击表情
        self.ui.tableWidget_emoji.cellClicked.connect(self.send_emoji)

    # 初始化
    def init_em(self):
        self.ui.tableWidget_emoji.setFocusPolicy(QtCore.Qt.NoFocus)
        for i in range(1, 34):
            path = "./img/emoji/emoji (%d).png" % (i + 1)
            row = int(i / self.ui.tableWidget_emoji.rowCount())
            column = int(i % self.ui.tableWidget_emoji.rowCount())
            tableWidgetItem = QTableWidgetItem()
            self.ui.tableWidget_emoji.setItem(row, column, tableWidgetItem)
            emotionIcon = QLabel()
            emotionIcon.setPixmap(QPixmap(path))
            emotionIcon.setScaledContents(True)
            self.ui.tableWidget_emoji.setCellWidget(row, column, emotionIcon)

    # 点击表情
    def send_emoji(self, row, col):
        self.row = row
        self.col = col
        self.signal.emit(1)
        self.close()

    # 返回结果
    def res(self):
        return self.row, self.col


# 聊天线程
class Thread_chat(QThread):
    # 设置自定义信号,传递字符串数据
    signal = pyqtSignal(str)

    # 用于传递聊天信息的套接字
    chat_sock = socket.socket()

    def __init__(self):
        super().__init__()

    # 线程自动从run函数执行
    def run(self):
        # 连接客户端的聊天端口
        self.chat_sock.connect((server_info["server_IP"], server_info["server_port_chat"]))
        print('连接到聊天端口')

        # 循环接收消息
        while True:
            # 接收消息的长度,限制长度15
            rep_len = self.chat_sock.recv(15).decode()

            # 接收出错
            if not rep_len:
                break

            # 去除回复长度的格式化,转为int
            rep_len = int(rep_len.strip())

            # 接收请求的正文
            rep = self.receive_server(rep_len, self.chat_sock)
            rep = rep.decode()

            # 返回收到的消息
            self.signal.emit(str(rep))

    # 接收服务器消息
    @staticmethod
    def receive_server(rep_len, chat_sock):
        rep = b''
        rep_size = 0

        # 接收回复内容
        while rep_size < rep_len:
            # 允许多次接收,保证收到全部内容
            data = chat_sock.recv(rep_len - rep_size)

            # 接收出错
            if not data:
                break

            # 合并所有消息
            rep += data
            rep_size += len(data)
        return rep

    # 发送消息
    def send_server(self, mes):
        mes = mes.encode()
        mes_len = '{:<15}'.format(len(mes))
        self.chat_sock.send(mes_len.encode())
        self.chat_sock.send(mes)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Client_Login()
    win.show()
    sys.exit(app.exec())
