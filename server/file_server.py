#!/usr/bin/python3
# -*- coding: utf-8 -*-

import socket
import sys
import os
import threading
import hashlib
import json
import user_reg_login


conf = json.load(open("server_conf.json"))  # 加载配置信息
dest_file_abs_path = os.path.abspath(sys.argv[0])
dest_file_parent_path = os.path.dirname(dest_file_abs_path)
dest_file_name = os.path.basename(dest_file_abs_path)


def get_file_md5(file_path):
    m = hashlib.md5()

    with open(file_path, "rb") as f:
        while True:
            data = f.read(1024)
            if len(data) == 0:
                break    
            m.update(data)
    
    return m.hexdigest().upper()


# def send_one_file(sock_conn, file_abs_path):
#     '''
#     函数功能：将一个文件发送给客户端
#     参数描述：
#         sock_conn 套接字对象
#         file_abs_path 待发送的文件的绝对路径
#     '''
#     file_name = file_abs_path[len(dest_file_parent_path):]
#     if file_name[0] == '\\' or file_name[0] == '/':
#         file_name = file_name[1:]

#     file_size = os.path.getsize(file_abs_path)
#     file_md5 = get_file_md5(file_abs_path)

#     file_name = file_name.encode()
#     file_name += b' ' * (300 - len(file_name))
#     file_size = "{:<15}".format(file_size).encode()

#     file_desc_info = file_name + file_size + file_md5.encode()

#     sock_conn.send(file_desc_info)
#     with open(file_abs_path, "rb") as f:
#         while True:
#             data = f.read(1024)
#             if len(data) == 0:
#                 break
#             sock_conn.send(data)


# def send_empty_dir(sock_conn, dir_abs_path):
#     '''
#     函数功能：将一个空文件夹发送给客户端
#     参数描述：
#         sock_conn 套接字对象
#         dir_abs_path 待发送的空文件夹的绝对路径
#     '''
#     file_name = dir_abs_path[len(dest_file_parent_path):]
#     if file_name[0] == '\\' or file_name[0] == '/':
#         file_name = file_name[1:]

#     file_size = -1
#     file_md5 = " " * 32

#     file_name = file_name.encode()
#     file_name += b' ' * (300 - len(file_name))
#     file_size = "{:<15}".format(file_size).encode()

#     file_desc_info = file_name + file_size + file_md5.encode()
#     sock_conn.send(file_desc_info)


# def send_dir(sock_conn):
#     '''
#     发送非空文件夹
#     '''
#     for root, dirs, files in os.walk(dest_file_abs_path):
#         if len(dirs) == 0 and len(files) == 0:
#             send_empty_dir(sock_conn, root)
#             continue

#         for f in files:
#             file_abs_path = os.path.join(root, f)
#             print(file_abs_path)
#             send_one_file(sock_conn, file_abs_path)


def user_service_thread(sock_conn,client_addr):
    try:
        data_len = sock_conn.recv(15).decode().rstrip()
        if len(data_len) > 0:
            data_len = int(data_len)

            recv_size = 0
            json_data = b""
            while recv_size < data_len:
                tmp = sock_conn.recv(data_len - recv_size)
                if tmp == 0:
                    break
                json_data += tmp
                recv_size += len(tmp)
            
            json_data = json_data.decode()
            req = json.loads(json_data)

            if req["op"] == 1:
                # 登录校验
                rsp = {"op": 1, "error_code": 0}  #将要发送给客户端的数据

                if user_reg_login.check_uname_pwd(req["args"]["uname"], req["args"]["passwd"]):  #如果校验失败则将"error_code"的值变为1发送给客户端
                    rsp["error_code"] = 1
                
                header_data = json.dumps(rsp).encode()
                data_len = "{:<15}".format(len(header_data)).encode()
                sock_conn.send(data_len)
                sock_conn.send(header_data)


                if not rsp["error_code"]: 
                    client_chat(sock_conn,client_addr) 
                    

            elif req["op"] == 2:
                # 用户注册
                rsp = {"op": 2, "error_code": 0}
                if not user_reg_login.user_reg(req["args"]["uname"], req["args"]["passwd"], req["args"]["phone"], req["args"]["email"]):
                    # 注册失败
                    rsp["error_code"] = 1

                rsp = json.dumps(rsp).encode()
                data_len = "{:<15}".format(len(rsp)).encode()
                sock_conn.send(data_len)
                sock_conn.send(rsp)            

            elif req["op"] == 3:
                # 校验用户名是否存在
                rsp = {"op": 3, "error_code": 0}

                ret = user_reg_login.check_user_name(req["args"]["uname"])
                if ret == 2:
                    rsp["error_code"] = 1
                
                rsp = json.dumps(rsp).encode()
                data_len = "{:<15}".format(len(rsp)).encode()
                sock_conn.send(data_len)
                sock_conn.send(rsp)            
    finally:
        sock_conn.close()

def client_chat(sock_conn, client_addr):
    try:
        while True:
                msg_len_data = sock_conn.recv(15)
                
                if not msg_len_data:    #接收客户端发送来的消息判断是否为0，为0则结束
                    break

                msg_len = int(msg_len_data.decode().rstrip())
                recv_size = 0
                msg_content_data = b""
                #print('ok')
                while recv_size < msg_len:          #开始接收正文
                    tmp_data = sock_conn.recv(msg_len - recv_size)
                    if not tmp_data:
                        break
                    msg_content_data += tmp_data
                    recv_size += len(tmp_data)
                else:
                    # 发送给其他所有在线的客户端
                    for sock_tmp, tmp_addr in client_socks:  #通过循环将刚收到的消息分别发送给登录了的用户
                        if sock_tmp is not sock_conn:
                            try:
                                sock_tmp.send(msg_len_data)
                                sock_tmp.send(msg_content_data)
                            except:
                                client_socks.remove((sock_tmp, tmp_addr))  #移除列表中下线的用户的ip和端口
                                sock_tmp.close()
                    continue
                break
    finally:
            client_socks.remove((sock_conn, client_addr))
            sock_conn.close()




sock_listen = socket.socket()
sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#端口复用
sock_listen.bind((conf["app_server_ip"], conf["app_server_port"]))
sock_listen.listen(5)
client_socks=[]
while True:
    sock_conn, client_addr = sock_listen.accept()
    print(client_addr, "已连接！")
    client_socks.append((sock_conn, client_addr))
    threading.Thread(target=user_service_thread, args=(sock_conn,client_addr )).start()

sock_listen.close()



