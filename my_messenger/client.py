import json
import sys
import time
import argparse
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_configs, get_message, send_message
from log.client_log_config import client_logger
from log.log_decorator import Log

CONFIGS = get_configs()


@Log()
# функция формирует presence-сообщение
def create_presence_message(CONFIGS):
    message = {
        CONFIGS.get('ACTION'): CONFIGS.get('PRESENCE'),
        CONFIGS.get('TIME'): time.ctime(time.time()),
        "type": "status",
        CONFIGS.get('USER'): {
            CONFIGS.get('ACCOUNT_NAME'): "Samoryad",
            "status": "Привет, сервер!"
        }
    }
    return message


@Log()
# функция проверки ответа сервера
def check_response(message):
    if CONFIGS.get('RESPONSE') in message:
        if message[CONFIGS.get('RESPONSE')] == 200:
            client_logger.debug('ответ от сервера получен')
            return f'200: OK, {message[CONFIGS.get("ALERT")]}'
        client_logger.error('произошла ошибка ответа сервера')
        return f'400: {message[CONFIGS.get("ERROR")]}'
    raise ValueError


def main():
    # global CONFIGS
    # параметры командной строки скрипта client.py <addr> [<port>]:
    parser = argparse.ArgumentParser(description='command line client parameters')
    parser.add_argument('addr', type=str, nargs='?', default=CONFIGS.get('DEFAULT_IP_ADDRESS'),
                        help='server ip address')
    parser.add_argument('port', type=int, nargs='?', default=CONFIGS.get('DEFAULT_PORT'), help='port')
    args = parser.parse_args()

    # проверка введённых параметров из командной строки вызова клиента
    try:
        server_address = args.addr
        server_port = int(args.port)
        if not 65535 >= server_port >= 1024:
            raise ValueError
    except IndexError:
        server_address = CONFIGS.get('DEFAULT_IP_ADDRESS')
        server_port = CONFIGS.get('DEFAULT_PORT')
        client_logger.warning('Подставлены значения адреса и порта по умолчанию')
    except ValueError:
        # print('Порт должен быть указан в пределах от 1024 до 65535')
        client_logger.critical('Порт должен быть указан в пределах от 1024 до 65535')
        sys.exit(1)

    # клиент создаёт сокет
    s = socket(AF_INET, SOCK_STREAM)

    # устанавливает соединение
    s.connect((server_address, server_port))

    # формирует и отправляет сообщение серверу;
    presence_message = create_presence_message(CONFIGS)
    send_message(s, presence_message, CONFIGS)

    # получает ответ сервера и проверяет сообщение сервера
    try:
        response = get_message(s, CONFIGS)
        checked_response = check_response(response)
        print(f'Ответ от сервера: {checked_response}')
        client_logger.info(f'Ответ от сервера: {checked_response}')
    except (ValueError, json.JSONDecodeError):
        # print('Ошибка декорирования сообщения')
        client_logger.error('Ошибка декорирования сообщения')

    # закрывает соединение
    s.close()


if __name__ == '__main__':
    main()
