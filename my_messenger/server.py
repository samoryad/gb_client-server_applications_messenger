import argparse
import json
import select
import sys
import time
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_configs, get_message, send_message, read_requests, write_responses
from log.server_log_config import server_logger
from log.log_decorator import log

CONFIGS = get_configs()


@log()
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


@log()
# функция проверки сообщения клиента
def check_message_from_chat_client(message, messages_list, CONFIGS):
    if CONFIGS.get('ACTION') in message \
            and message[CONFIGS.get('ACTION')] == CONFIGS.get('MESSAGE') \
            and CONFIGS.get('TIME') in message \
            and CONFIGS.get('ACCOUNT_NAME') in message \
            and message[CONFIGS.get('ACCOUNT_NAME')] == 'Samoryad':
        server_logger.info('сообщение клиента успешно проверено. привет, клиент')
        messages_list.append({
            CONFIGS.get('RESPONSE'): 200,
            CONFIGS.get('ALERT'): message[CONFIGS.get('MESSAGE_TEXT')]
        })
    else:
        server_logger.error('сообщение от клиента некорректно')
        messages_list.append({
            CONFIGS.get('RESPONSE'): 400,
            CONFIGS.get('ERROR'): 'Bad request'
        })


# параметры командной строки скрипта server.py -p <port>, -a <addr>:
parser = argparse.ArgumentParser(description='command line server parameters')
parser.add_argument('-a', '--addr', type=str, default='', help='ip address')
parser.add_argument('-p', '--port', type=int, default=CONFIGS.get('DEFAULT_PORT'), help='tcp-port')
args = parser.parse_args()


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
    # Таймаут для операций с сокетом (1 секунда)
    s.settimeout(0.5)

    clients = []
    messages = []

    while True:
        try:
            # принимает запрос на установку соединения
            client, addr = s.accept()
        except OSError as e:
            pass  # timeout вышел
        else:
            server_logger.info(f'Установлено соединение с: {str(addr)}')
            clients.append(client)

        r_list = []
        w_list = []
        try:
            if clients:
                r_list, w_list, e_list = select.select(clients, clients, [], 2)
        except OSError:
            pass  # Ничего не делать, если какой-то клиент отключился
        if r_list:
            for client_with_message in r_list:
                try:
                    check_message_from_chat_client(get_message(client_with_message, CONFIGS), messages, CONFIGS)
                except:
                    server_logger.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                    clients.remove(client_with_message)
        if messages and w_list:
            message = {
                CONFIGS.get('RESPONSE'): 200,
                CONFIGS.get('ALERT'): messages[0]['alert'],
            }

            # print(messages)
            del messages[0]
            for waiting_client in w_list:
                try:
                    send_message(waiting_client, message, CONFIGS)
                except:
                    server_logger.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                    clients.remove(waiting_client)

        # пока оставил от урока 7
        # requests = read_requests(r_list, clients, CONFIGS)  # Сохраним запросы клиентов
        # if requests:
        #     print(requests)
        #     write_responses(requests, w_list, clients, CONFIGS)  # Выполним отправку ответов клиентам

        # пока оставил от урока 6
        # принимает сообщение клиента и проверяет его; при успешной проверке, отсылает ответ 200;
        # try:
        #     message = get_message(client, CONFIGS)
        #     print(f'Сообщение: {message}, было отправлено клиентом: {addr}')
        #     server_logger.debug(f'получено сообщение {message} от клиента {addr}')
        #     response = check_message(message)
        #     send_message(client, response, CONFIGS)
        #     client.close()
        # except (ValueError, json.JSONDecodeError):
        #     # print('Принято некорректное сообщение от клиента')
        #     server_logger.error('Принято некорректное сообщение от клиента')
        #     client.close()


if __name__ == '__main__':
    print('Стартуем сервер')
    main()
