from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_settings, get_data_from_message, send_message

# сервер создаёт сокет
s = socket(AF_INET, SOCK_STREAM)
# привязывает сокет к IP-адресу и порту машины
s.bind(('', get_settings()['port']))
# готов принимать соединения
s.listen(5)

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
