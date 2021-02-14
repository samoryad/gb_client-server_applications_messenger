import argparse
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_settings, get_data_from_message, send_message

# сервер создаёт сокет
s = socket(AF_INET, SOCK_STREAM)
# привязывает сокет к IP-адресу и порту машины
s.bind(('', get_settings()['port']))
# готов принимать соединения
s.listen(5)

# параметры командной строки скрипта server.py -p <port>, -a <addr>:
parser = argparse.ArgumentParser(description='command line server parameters')
parser.add_argument('-a', '--addr', type=str, nargs='?', default='', help='ip address')
parser.add_argument('-p', '--port', type=int, nargs='?', default=7777, help='tcp-port')
args = parser.parse_args()
print(args)

while True:
    # принимает запрос на установку соединения
    client, addr = s.accept()
    # принимает сообщение клиента;
    print('Сообщение: ', get_data_from_message(client.recv(1000000)), ', было отправлено клиентом: ', addr)
    # формирует ответ клиенту;
    msg = {
        "response": '200',
        "alert": 'Привет, клиент!'
    }
    # отправляет ответ клиенту;
    send_message(client, msg)
    # закрывает соединение
    client.close()
