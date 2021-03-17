import argparse
import select
import sys
import time
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_configs, get_message, send_message
from log.server_log_config import server_logger
from log.log_decorator import log

CONFIGS = get_configs()


class Server:
    '''класс сервера'''

    def __init__(self):
        # параметры командной строки скрипта server.py -p <port>, -a <addr>:
        parser = argparse.ArgumentParser(description='command line server parameters')
        parser.add_argument('-a', '--addr', type=str, default='', help='ip address')
        parser.add_argument('-p', '--port', type=int, default=CONFIGS.get('DEFAULT_PORT'), help='tcp-port')
        self.args = parser.parse_args()

    @log()
    # метод парсера аргументов командной строки
    def arg_parser(self):
        # проверка параметров вызова ip-адреса и порта из командной строки
        try:
            if '-a' or '--addr' in sys.argv:
                listen_address = self.args.addr
            else:
                listen_address = ''
        except IndexError:
            # print('После \'-a\' - необходимо указать адрес')
            server_logger.critical('После \'-a\' - необходимо указать адрес')
            sys.exit(1)

        try:
            if '-p' or '--port' in sys.argv:
                listen_port = self.args.port
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

        return listen_address, listen_port

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

    def main(self):
        listen_address, listen_port = self.arg_parser()
        # сервер создаёт сокет
        sock = socket(AF_INET, SOCK_STREAM)
        # привязывает сокет к IP-адресу и порту машины
        sock.bind((listen_address, listen_port))
        # готов принимать соединения
        sock.listen(CONFIGS.get('MAX_CONNECTIONS'))
        # Таймаут для операций с сокетом (1 секунда)
        sock.settimeout(0.5)

        clients = []
        messages = []

        while True:
            try:
                # принимает запрос на установку соединения
                client, addr = sock.accept()
            except OSError as e:
                pass  # timeout вышел
            else:
                server_logger.info(f'Установлено соединение с: {str(addr)}')
                response = self.check_presence_message(get_message(client, CONFIGS), CONFIGS)
                send_message(client, response, CONFIGS)
                clients.append(client)

            r_list = []
            w_list = []
            try:
                if clients:
                    r_list, w_list, e_list = select.select(clients, clients, [], 2)
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
                        messages.append(answer)
                        # print(messages)
                    except:
                        server_logger.info(
                            f'Клиент {client_with_message.getpeername()} отключился от сервера - r_list.')
                        clients.remove(client_with_message)

            # если есть сообщения в списке ответов после проверки (200 или 400) и есть слушающие клиенты
            if messages and w_list:
                # print(f' w_list --- {w_list}\n')
                # print(f' messages --- {messages}\n')

                # то формируем ответное сообщение
                message = {
                    CONFIGS['ACTION']: CONFIGS['MESSAGE'],
                    CONFIGS['TIME']: time.ctime(time.time()),
                    CONFIGS['TO_USER']: messages[0].get('to'),
                    CONFIGS['FROM_USER']: messages[0].get('from'),
                    CONFIGS['MESSAGE']: messages[0].get('message')
                }
                # print(message)
                # удаляем сообщение из списка ответов после проверки
                del messages[0]

                # отправляем ждущим ответа клиентам сформированное сообщение
                for waiting_client in w_list:
                    # print(f' waiting_client --- {waiting_client}\n')
                    try:
                        send_message(waiting_client, message, CONFIGS)
                    except:
                        server_logger.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                        clients.remove(waiting_client)


if __name__ == '__main__':
    print('Стартуем сервер')
    server = Server()
    server.main()
