import json
import sys
import threading
import time
import argparse
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_configs, get_message, send_message
from log.client_log_config import client_logger
from log.log_decorator import Log
from errors import ReqFieldMissingError, ServerError, IncorrectDataReceivedError

CONFIGS = get_configs()


class Client:

    def __init__(self):
        # параметры командной строки скрипта client.py <addr> [<port>]:
        parser = argparse.ArgumentParser(description='command line client parameters')
        parser.add_argument('addr', type=str, nargs='?', default=CONFIGS.get('DEFAULT_IP_ADDRESS'),
                            help='server ip address')
        parser.add_argument('port', type=int, nargs='?', default=CONFIGS.get('DEFAULT_PORT'), help='port')
        parser.add_argument('-c', '--client', type=str, default=CONFIGS.get('DEFAULT_CLIENT_MODE'),
                            help='client mode - "send" or "listen"(default)')
        args = parser.parse_args()
        # print(args)

        # проверка введённых параметров из командной строки вызова клиента
        try:
            self.server_address = args.addr
            self.server_port = int(args.port)
            if not 65535 >= self.server_port >= 1024:
                raise ValueError
        except IndexError:
            self.server_address = CONFIGS.get('DEFAULT_IP_ADDRESS')
            self.server_port = CONFIGS.get('DEFAULT_PORT')
            client_logger.warning('Подставлены значения адреса и порта по умолчанию')
        except ValueError:
            # print('Порт должен быть указан в пределах от 1024 до 65535')
            client_logger.critical('Порт должен быть указан в пределах от 1024 до 65535')
            sys.exit(1)

    @Log()
    # функция формирует presence-сообщение
    def create_presence_message(self, CONFIGS):
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
    def check_response(self, message, CONFIGS):
        if CONFIGS.get('RESPONSE') in message:
            if message[CONFIGS.get('RESPONSE')] == 200:
                client_logger.debug('ответ от сервера получен')
                return f'200: OK, {message[CONFIGS.get("ALERT")]}'
            client_logger.error('произошла ошибка ответа сервера')
            return f'400: {message[CONFIGS.get("ERROR")]}'
        raise ValueError

    def help_text(self):
        print('Поддерживаемые команды:')
        print('to_user - отправить сообщение конкретному пользователю. Кому и текст будет запрошены отдельно.')
        print('to_all - отправить сообщение всем. Текст будет запрошен отдельно.')
        print('help - вывести подсказки по командам')
        print('q - выход из программы')

    @Log()
    def create_user_message_to_all(self, sock, CONFIGS, username='Guest'):
        message = input('Введите сообщение для отправки (для завершения работы - "q"): ')
        if message == 'q':
            sock.close()
            client_logger.info('Завершение работы по команде пользователя')
            print('Спасибо за использование нашего сервиса')
            sys.exit(0)
        message_dict = {
            CONFIGS['ACTION']: CONFIGS['MESSAGE'],
            CONFIGS['TIME']: time.ctime(time.time()),
            CONFIGS['TO_USER']: '#',
            CONFIGS['FROM_USER']: username,
            CONFIGS['MESSAGE']: message
        }
        client_logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(sock, message_dict, CONFIGS)
            client_logger.info(f'Отправлено сообщение всем пользователям от {username}')
        except:
            client_logger.critical('Потеряно соединение с сервером.')
            sys.exit(1)

    @Log()
    def create_message_to_user(self, sock, account_name='Guest'):
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            CONFIGS['ACTION']: CONFIGS['MESSAGE'],
            CONFIGS['TIME']: time.ctime(time.time()),
            CONFIGS['TO_USER']: to_user,
            CONFIGS['FROM_USER']: account_name,
            'encoding': CONFIGS['ENCODING'],
            CONFIGS['MESSAGE']: message
        }
        client_logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(sock, message_dict, CONFIGS)
            client_logger.info(f'Отправлено сообщение от {account_name} для пользователя {to_user}')
        except:
            client_logger.critical('Потеряно соединение с сервером.')
            sys.exit(1)

    @Log()
    def create_exit_message(self, account_name, CONFIGS):
        return {
            CONFIGS.get('ACTION'): "quit",
            CONFIGS.get('TIME'): time.ctime(time.time()),
            CONFIGS['ACCOUNT_NAME']: account_name
        }

    @Log()
    def check_message_from_server(self, sock, my_username):
        while True:
            try:
                message = get_message(sock, CONFIGS)
                if CONFIGS['ACTION'] in message and message[CONFIGS['ACTION']] == CONFIGS['MESSAGE'] and \
                        CONFIGS['FROM_USER'] in message and CONFIGS['TO_USER'] in message \
                        and CONFIGS['MESSAGE'] in message:
                    if message[CONFIGS['TO_USER']] == my_username:
                        print(f'\nПолучено сообщение от пользователя {message[CONFIGS["FROM_USER"]]} '
                              f'для {message[CONFIGS["TO_USER"]]}: {message[CONFIGS["MESSAGE"]]}')
                        client_logger.info(f'Получено сообщение от пользователя {message[CONFIGS["FROM_USER"]]} '
                                           f'для {message[CONFIGS["TO_USER"]]}: {message[CONFIGS["MESSAGE"]]}')
                    if message[CONFIGS['TO_USER']] == '#':
                        print(f'\nПолучено сообщение от пользователя {message[CONFIGS["FROM_USER"]]} для всех: '
                              f'{message[CONFIGS["MESSAGE"]]}')
                        client_logger.info(
                            f'Получено сообщение от пользователя {message[CONFIGS["FROM_USER"]]} для всех: '
                            f'{message[CONFIGS["MESSAGE"]]}')
                else:
                    client_logger.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataReceivedError:
                client_logger.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                client_logger.critical(f'Потеряно соединение с сервером.')
                break

    @Log()
    def user_interactive(self, sock, username):
        print(self.help_text())
        while True:
            command = input('Введите команду: ')
            if command == 'to_user':
                self.create_message_to_user(sock, username)
            elif command == 'to_all':
                self.create_user_message_to_all(sock, CONFIGS, username)
            elif command == 'help':
                print(self.help_text())
            elif command == 'q':
                send_message(sock, self.create_exit_message(username, CONFIGS), CONFIGS)
                print('Завершение соединения.')
                client_logger.info('Завершение работы по команде пользователя.')
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def main(self):
        # При использовании оператора with сокет будет автоматически закрыт
        with socket(AF_INET, SOCK_STREAM) as sock:  # Создать сокет TCP
            try:
                # устанавливает соединение
                sock.connect((self.server_address, self.server_port))
                send_message(sock, self.create_presence_message(CONFIGS), CONFIGS)
                answer = self.check_response(get_message(sock, CONFIGS), CONFIGS)
                client_logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
                # print(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            except json.JSONDecodeError:
                client_logger.error('Не удалось декодировать полученную Json строку.')
                sys.exit(1)
            except ServerError as error:
                client_logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
                sys.exit(1)
            except ReqFieldMissingError as missing_error:
                client_logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
                sys.exit(1)
            except ConnectionRefusedError:
                client_logger.critical(
                    f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                    f'конечный компьютер отверг запрос на подключение.')
                sys.exit(1)
            else:
                if 'send' in sys.argv:
                    client_name = 'Samoryad'
                    print(f'клиент в режиме отправки сообщения, пока это {client_name}')
                    client_logger.debug(f'клиент в режиме отправки сообщения, пока это {client_name}')
                    receiver = threading.Thread(target=self.check_message_from_server, args=(sock, client_name))
                    receiver.daemon = True
                    user_interface = threading.Thread(target=self.user_interactive, args=(sock, client_name))
                    user_interface.daemon = True
                    receiver.start()
                    user_interface.start()
                    user_interface.join()

                else:
                    client_name = 'Gogi'
                    print(f'клиент в режиме слушателя, пока это {client_name}')
                    client_logger.debug(f'клиент в режиме слушателя, пока это {client_name}')
                    receiver = threading.Thread(target=self.check_message_from_server, args=(sock, client_name))
                    receiver.daemon = True
                    receiver.start()
                    receiver.join()


if __name__ == '__main__':
    client = Client()
    client.main()
