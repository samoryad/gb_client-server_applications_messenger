import argparse
import select
import sys
import threading
import time
import socket
from common.utils import get_configs, get_message, send_message
from log.server_log_config import server_logger
from log.log_decorator import log
from metaclasses import ServerVerifier
from my_messenger.server_storage import ServerStorage
from server_descriptor import CheckPort

CONFIGS = get_configs()


@log()
# функция парсера аргументов командной строки
def arg_parser():
    # параметры командной строки скрипта server.py -p <port>, -a <addr>:
    parser = argparse.ArgumentParser(description='command line server parameters')
    parser.add_argument('-a', '--addr', type=str, default='', help='ip address')
    parser.add_argument('-p', '--port', type=int, default=CONFIGS.get('DEFAULT_PORT'), help='tcp-port')
    args = parser.parse_args()
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
    except IndexError:
        # print('После -\'p\' необходимо указать порт')
        server_logger.critical('После -\'p\' необходимо указать порт')
        sys.exit(1)
    except ValueError:
        # print('Порт должен быть указан в пределах от 1024 до 65535')
        server_logger.critical('Порт должен быть указан в пределах от 1024 до 65535')

    return listen_address, listen_port


class Server(threading.Thread, metaclass=ServerVerifier):
    # """класс сервера"""
    listen_port = CheckPort()

    def __init__(self, listen_address, listen_port, database):
        # параментры подключения
        self.addr = listen_address
        self.port = listen_port

        # база данных сервера
        self.database = database

        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # конструктор предка
        super().__init__()

    @log()
    # метод проверки сообщения клиента
    def check_presence_message(self, message, CONFIGS):
        if CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == CONFIGS.get('PRESENCE') \
                and CONFIGS.get('TIME') in message \
                and CONFIGS.get('USER') in message \
                and message[CONFIGS.get('USER')][CONFIGS.get("ACCOUNT_NAME")] == 'Samoryad':
            server_logger.info('presence сообщение клиента успешно проверено. привет, клиент')
            return {
                CONFIGS.get('RESPONSE'): 200,
                CONFIGS.get('ALERT'): 'Привет, клиент!'
            }
        server_logger.error('presence сообщение от клиента некорректно')
        return {
            CONFIGS.get('RESPONSE'): 400,
            CONFIGS.get('ERROR'): 'Bad request'
        }

    @log()
    # метод проверки сообщения клиента
    def check_message_from_chat(self, message, CONFIGS):
        server_logger.debug(f'Обработка сообщения от клиента {message[CONFIGS.get("FROM_USER")]}: {message}')
        if CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == CONFIGS.get('MESSAGE') \
                and CONFIGS.get('TIME') in message \
                and CONFIGS.get('TO_USER') in message \
                and message[CONFIGS.get('FROM_USER')] == 'Samoryad':
            if message[CONFIGS.get('TO_USER')] == '#':
                server_logger.info(
                    f'сообщение для всех от клиента {message[CONFIGS.get("FROM_USER")]} успешно проверено')
            else:
                server_logger.info(f'личное сообщение от клиента {message[CONFIGS.get("FROM_USER")]} '
                                   f'для пользователя {message[CONFIGS.get("TO_USER")]} успешно проверено')
            return {
                CONFIGS.get('RESPONSE'): 200,
                CONFIGS.get('TO_USER'): message[CONFIGS.get('TO_USER')],
                CONFIGS['FROM_USER']: message[CONFIGS.get('FROM_USER')],
                CONFIGS.get('MESSAGE'): message[CONFIGS.get('MESSAGE')]
            }
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == 'quit':
            return {CONFIGS.get('ACTION'): 'quit'}
        else:
            server_logger.error('сообщение из чата клиента некорректно')
            return {
                CONFIGS.get('RESPONSE'): 400,
                CONFIGS.get('ERROR'): 'Bad request'
            }

    def init_socket(self):
        # server_logger.info(
        #     f'Запущен сервер, порт для подключений: {self.port} ,'
        #     f' адрес с которого принимаются подключения: {self.addr}.'
        #     f' Если адрес не указан, принимаются соединения с любых адресов.')

        # сервер создаёт сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # привязывает сокет к IP-адресу и порту машины
        sock.bind((self.addr, self.port))
        # Таймаут для операций с сокетом (1 секунда)
        sock.settimeout(0.5)

        self.sock = sock
        # готов принимать соединения
        self.sock.listen(CONFIGS.get('MAX_CONNECTIONS'))

    def run(self):
        # инициализируем сокет
        self.init_socket()

        while True:
            try:
                # принимает запрос на установку соединения
                client, addr = self.sock.accept()
            except OSError as e:
                pass  # timeout вышел
            else:
                server_logger.info(f'Установлено соединение с: {str(addr)}')
                response = self.check_presence_message(get_message(client, CONFIGS), CONFIGS)
                send_message(client, response, CONFIGS)
                self.clients.append(client)

            r_list = []
            w_list = []
            e_list = []
            try:
                if self.clients:
                    r_list, w_list, e_list = select.select(self.clients, self.clients, [], 2)
            except OSError:
                # Ничего не делать, если какой-то клиент отключился
                pass

            # проверяем список клиентов, из которых нужно что-то прочитать
            if r_list:
                for client_with_message in r_list:
                    # ловим от них сообщение и проверяем его на корректность и вносим в список
                    # сообщений messages (200 или 400)
                    try:
                        answer = self.check_message_from_chat(get_message(client_with_message, CONFIGS),
                                                              CONFIGS)
                        self.messages.append(answer)
                        # print(messages)
                    except:
                        server_logger.info(
                            f'Клиент {client_with_message.getpeername()} отключился от сервера - r_list.')
                        self.clients.remove(client_with_message)

            # если есть сообщения в списке ответов после проверки (200 или 400) и есть слушающие клиенты
            if self.messages and w_list:
                # print(f' w_list --- {w_list}\n')
                # print(f' messages --- {messages}\n')

                # то формируем ответное сообщение
                message = {
                    CONFIGS['ACTION']: CONFIGS['MESSAGE'],
                    CONFIGS['TIME']: time.ctime(time.time()),
                    CONFIGS['TO_USER']: self.messages[0].get('to'),
                    CONFIGS['FROM_USER']: self.messages[0].get('from'),
                    CONFIGS['MESSAGE']: self.messages[0].get('message')
                }
                # print(message)
                # удаляем сообщение из списка ответов после проверки
                del self.messages[0]

                # отправляем ждущим ответа клиентам сформированное сообщение
                for waiting_client in w_list:
                    # print(f' waiting_client --- {waiting_client}\n')
                    try:
                        send_message(waiting_client, message, CONFIGS)
                    except:
                        server_logger.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                        self.clients.remove(waiting_client)


def print_help():
    print('Поддерживаемые комманды:')
    print('all_users - список известных пользователей')
    print('active - список подключенных пользователей')
    print('show_history - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    # грузим парамтры командной строки
    listen_address, listen_port = arg_parser()

    # создаём экземпляр базы данных
    database = ServerStorage()

    # создаём экземпляр класса сервер
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # печатаем справку
    print_help()

    # основной цикл сервера
    while True:
        command = input('Введите комманду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'all_users':
            for user in sorted(database.all_users_list()):
                print(f'Пользователь {user[1]}, последний вход: {user[2]}')
        elif command == 'active':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[1]}, подключен: {user[2]}:{user[3]}, время установки соединения: {user[4]}')
        elif command == 'show_history':
            for user in sorted(database.show_history()):
                print(f'Пользователь: {user[1]} время входа: {user[2]}. Вход с: {user[3]}:{user[4]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    print('Стартуем сервер')
    main()
