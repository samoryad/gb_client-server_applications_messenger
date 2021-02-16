import argparse
import json
import sys
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_configs, get_message, send_message
from log.server_log_config import server_logger

CONFIGS = get_configs()


# функция проверки сообщения клиента
def check_message(message):
    if CONFIGS.get('ACTION') in message \
            and message[CONFIGS.get('ACTION')] == CONFIGS.get('PRESENCE') \
            and CONFIGS.get('TIME') in message \
            and CONFIGS.get('USER') in message \
            and message[CONFIGS.get('USER')][CONFIGS.get("ACCOUNT_NAME")] == 'Samoryad':
        server_logger.info('сообщение клиента успешно проверено. привет, клиент')
        return {
            CONFIGS.get('RESPONSE'): 200,
            CONFIGS.get('ALERT'): 'Привет, клиент!'
        }
    server_logger.error('сообщение от клиента некорректно')
    return {
        CONFIGS.get('RESPONSE'): 400,
        CONFIGS.get('ERROR'): 'Bad request'
    }


# параметры командной строки скрипта server.py -p <port>, -a <addr>:
parser = argparse.ArgumentParser(description='command line server parameters')
parser.add_argument('-a', '--addr', type=str, default='', help='ip address')
parser.add_argument('-p', '--port', type=int, default=CONFIGS.get('DEFAULT_PORT'), help='tcp-port')
args = parser.parse_args()
print(args)


def main():
    # проверка параметров вызова ip-адреса и порта из командной строки
    try:
        if '-a' or '--addr' in sys.argv:
            listen_address = args.addr
        else:
            listen_address = ''
    except IndexError:
        # print('После \'-a\' - необходимо указать адрес')
        server_logger.critical('После \'-a\' - необходимо указать адрес')
        sys.exit(1)

    try:
        if '-p' or '--port' in sys.argv:
            listen_port = args.port
        else:
            listen_port = CONFIGS.get('DEFAULT_PORT')
        if not 65535 >= listen_port >= 1024:
            raise ValueError
    except IndexError:
        # print('После -\'p\' необходимо указать порт')
        server_logger.critical('После -\'p\' необходимо указать порт')
        sys.exit(1)
    except ValueError:
        # print('Порт должен быть указан в пределах от 1024 до 65535')
        server_logger.critical('Порт должен быть указан в пределах от 1024 до 65535')
        sys.exit(1)

    # сервер создаёт сокет
    s = socket(AF_INET, SOCK_STREAM)
    # привязывает сокет к IP-адресу и порту машины
    s.bind((listen_address, listen_port))
    # готов принимать соединения
    s.listen(CONFIGS.get('MAX_CONNECTIONS'))

    while True:
        # принимает запрос на установку соединения
        client, addr = s.accept()
        # принимает сообщение клиента и проверяет его; при успешной проверке, отсылает ответ 200;
        try:
            message = get_message(client, CONFIGS)
            print(f'Сообщение: {message}, было отправлено клиентом: {addr}')
            server_logger.debug(f'получено сообщение {message} от клиента {addr}')
            response = check_message(message)
            send_message(client, response, CONFIGS)
            client.close()
        except (ValueError, json.JSONDecodeError):
            # print('Принято некорректное сообщение от клиента')
            server_logger.error('Принято некорректное сообщение от клиента')
            client.close()


if __name__ == '__main__':
    main()
