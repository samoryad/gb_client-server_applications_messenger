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


def create_user_message(sock, CONFIGS, account_name='Guest'):
    message = input('Введите сообщение для отправки (для завершения работы - "q"): ')
    if message == 'q':
        sock.close()
        client_logger.info('Завершение работы по команде пользователя')
        print('Спасибо за использование нашего сервиса')
        sys.exit(0)
    message_dict = {
        CONFIGS['ACTION']: CONFIGS['MESSAGE'],
        CONFIGS['TIME']: time.ctime(time.time()),
        CONFIGS['ACCOUNT_NAME']: account_name,
        CONFIGS['MESSAGE_TEXT']: message
    }
    client_logger.debug(f'Сформирован словарь сообщения: {message_dict}')
    return message_dict


def handle_server_message(message, CONFIG):
    if CONFIG['ACTION'] in message and message[CONFIG['ACTION']] == CONFIG['MESSAGE'] and CONFIG['SENDER'] in message and CONFIG['MESSAGE_TEXT'] in message:
        print(f'Получено сообщение от пользователя' f'{message[CONFIG["SENDER"]]}:\n{message[CONFIG["MESSAGE_TEXT"]]}')
        client_logger.info(f'Получено сообщение от пользователя'
                           f'{message[CONFIG["SENDER"]]}:\n{message[CONFIG["MESSAGE_TEXT"]]}')
    else:
        client_logger.error(f'Получено некорректное сообщение с сервера: {message}')


def main():
    # global CONFIGS
    # параметры командной строки скрипта client.py <addr> [<port>]:
    parser = argparse.ArgumentParser(description='command line client parameters')
    parser.add_argument('addr', type=str, nargs='?', default=CONFIGS.get('DEFAULT_IP_ADDRESS'),
                        help='server ip address')
    parser.add_argument('port', type=int, nargs='?', default=CONFIGS.get('DEFAULT_PORT'), help='port')
    parser.add_argument('-c', '--client', type=str, default=CONFIGS.get('DEFAULT_CLIENT_MODE'),
                        help='client mode - "send" or "listen"(default)')
    args = parser.parse_args()
    print(args)

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

    responses = []
    # При использовании оператора with сокет будет автоматически закрыт
    with socket(AF_INET, SOCK_STREAM) as sock:  # Создать сокет TCP
        # устанавливает соединение
        sock.connect((server_address, server_port))
        if 'send' in sys.argv:
            print('клиент в режиме отправки сообщения')
            while True:
                try:
                    # формируем и отправляем сообщение (create_user_message - по спецификации)
                    send_message(sock, create_user_message(sock, CONFIGS, 'Samoryad'), CONFIGS)

                    # Ловим сообщение от сервера и выводим на экран
                    # data = sock.recv(CONFIGS.get('MAX_PACKAGE_LENGTH')).decode(CONFIGS.get('ENCODING'))
                    # print('Ответ: ', data)

                    # ловим сообщение от сервера и проверяем
                    response = get_message(sock, CONFIGS)
                    print(response)
                    checked_response = check_response(response)
                    print(f'Ответ от сервера: {checked_response}')
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    client_logger.error(f'Соединение с сервером {server_address} было потеряно.')
        else:
            print('клиент в режиме слушателя')
            while True:
                try:
                    data = sock.recv(CONFIGS.get('MAX_PACKAGE_LENGTH')).decode(CONFIGS.get('ENCODING'))
                    if data:
                        # responses.append(data)
                        print('Ответ: ', data)
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    client_logger.error(f'Соединение с сервером {server_address} было потеряно.')

        # пока оставил от урока 6
        # формирует и отправляет сообщение серверу;
        # presence_message = create_presence_message(CONFIGS)
        # send_message(sock, presence_message, CONFIGS)
        #
        # # получает ответ сервера и проверяет сообщение сервера
        # try:
        #     response = get_message(s, CONFIGS)
        #     checked_response = check_response(response)
        #     print(f'Ответ от сервера: {checked_response}')
        #     client_logger.info(f'Ответ от сервера: {checked_response}')
        # except (ValueError, json.JSONDecodeError):
        #     # print('Ошибка декорирования сообщения')
        #     client_logger.error('Ошибка декорирования сообщения')
        #
        # # закрывает соединение
        # s.close()


if __name__ == '__main__':
    main()
