import time
from socket import socket, AF_INET, SOCK_STREAM
# для реализации через configs.py
# from common.configs import PORT, HOST
from common.utils import get_settings, get_data_from_message, send_message

# клиент создаёт сокет
s = socket(AF_INET, SOCK_STREAM)

# для реализации через configs.py
# s.connect(HOST, PORT)

# устанавливает соединение
s.connect((get_settings()['host'], get_settings()['port']))

# формирует presence-сообщение
msg = {
    "action": "presence",
    "time": time.ctime(time.time()),
    "type": "status",
    "user": {
        "account_name": "Samoryad",
        "status": "Привет, сервер!"
    }
}

# отправляет сообщение серверу;
send_message(s, msg)
# получает ответ сервера и разбирает сообщение сервера
print('Сообщение от сервера: ', get_data_from_message(s.recv(1000000)))
# закрывает соединение
s.close()
