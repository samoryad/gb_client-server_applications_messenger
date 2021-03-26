import json
import sys
import threading
import time
import argparse
import socket
from common.utils import get_configs, get_message, send_message
from log.client_log_config import client_logger
from log.log_decorator import Log, log
from errors import ReqFieldMissingError, ServerError, IncorrectDataReceivedError
from my_messenger.client_storage import ClientDatabase
from my_messenger.metaclasses import ClientVerifier

CONFIGS = get_configs()

# объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


# класс формировки и отправки сообщений на сервер и взаимодействия с пользователем.
class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    # метод создания словаря с сообщением о выходе.
    def create_exit_message(self):
        return {
            CONFIGS.get('ACTION'): CONFIGS.get('EXIT'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS['ACCOUNT_NAME']: self.account_name
        }

    # метод запрашивает кому отправить сообщение и формирует само сообщение и
    # отправляет полученные данные на сервер.
    def create_message(self):
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')

        # проверяем, что получатель существует
        with database_lock:
            if not self.database.check_user(to_user):
                client_logger.error(f'Попытка отправить сообщение незарегистрированому получателю: {to_user}')
                return
        # формируем сообщение
        message_dict = {
            CONFIGS['ACTION']: CONFIGS['MESSAGE'],
            CONFIGS['FROM_USER']: self.account_name,
            CONFIGS['TO_USER']: to_user,
            CONFIGS['TIME']: time.time(),
            CONFIGS['MESSAGE_TEXT']: message
        }
        client_logger.debug(f'Сформирован словарь сообщения: {message_dict}')

        # сохраняем сообщения для истории
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        # необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
            try:
                send_message(self.sock, message_dict, CONFIGS)
                client_logger.info(f'Отправлено сообщение для пользователя {to_user}')
            except OSError as err:
                if err.errno:
                    client_logger.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    client_logger.error('Не удалось передать сообщение. Таймаут соединения')

    # метод взаимодействия с пользователем:
    # запрашивает команды, отправляет сообщения
    def run(self):
        self.help_text()
        while True:
            command = input('Введите команду: ')
            # если отправка сообщения - соответствующий метод
            if command == 'message':
                self.create_message()

            # вывод справки по командам
            elif command == 'help':
                self.help_text()

            # если введён выход, тправляем сообщение серверу о выходе
            elif command == 'exit':
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message(), CONFIGS)
                    except:
                        pass
                    print('Завершение соединения.')
                    client_logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break

            # Список контактов
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts()

            # история сообщений.
            elif command == 'history':
                self.print_history()

            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    # метод вывода команд для ввода
    def help_text(self):
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    # метод вывода истории сообщений
    def print_history(self):
        request = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if request == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}')
            elif request == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(
                        f'\nСообщение от пользователя: {message[0]}, '
                        f'пользователю {message[1]} от {message[3]}\n{message[2]}')

    # метод изменения контактов
    def edit_contacts(self):
        client_command = input('Для удаления введите del, для добавления add: ')
        if client_command == 'del':
            to_del_contact = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.database.check_contact(to_del_contact):
                    self.database.del_contact(to_del_contact)
                else:
                    client_logger.error('Попытка удаления несуществующего контакта.')
        elif client_command == 'add':
            # проверка на возможность создания такого контакта
            to_add_contact = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(to_add_contact):
                with database_lock:
                    self.database.add_contact(to_add_contact)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, to_add_contact)
                    except ServerError:
                        client_logger.error('Не удалось отправить информацию на сервер.')


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль , сохраняет в базу.
class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    # Основной цикл приёмника сообщений, принимает сообщения, выводит в консоль. Завершается при потере соединения.
    def run(self):
        while True:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то второй поток может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock, CONFIGS)

                # Принято некорректное сообщение
                except IncorrectDataReceivedError:
                    client_logger.error(f'Не удалось декодировать полученное сообщение.')
                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        client_logger.critical(f'Потеряно соединение с сервером.')
                        break
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    client_logger.critical(f'Потеряно соединение с сервером.')
                    break
                # Если пакет корретно получен выводим в консоль и записываем в базу.
                else:
                    if CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                            'MESSAGE') and CONFIGS.get('FROM_USER') in message and CONFIGS.get(
                        'TO_USER') in message and CONFIGS.get('MESSAGE_TEXT') in message and message[
                        CONFIGS.get('TO_USER')] == self.account_name:
                        print(f'\nПолучено сообщение от пользователя {message[CONFIGS.get("FROM_USER")]}:'
                              f'\n{message[CONFIGS.get("MESSAGE_TEXT")]}')
                        # Захватываем работу с базой данных и сохраняем в неё сообщение
                        with database_lock:
                            try:
                                self.database.save_message(message[CONFIGS.get('FROM_USER')], self.account_name,
                                                           message[CONFIGS.get('MESSAGE_TEXT')])
                            except:
                                client_logger.error('Ошибка взаимодействия с базой данных')

                        client_logger.info(
                            f'Получено сообщение от пользователя {message[CONFIGS.get("FROM_USER")]}:'
                            f'\n{message[CONFIGS.get("MESSAGE_TEXT")]}')
                    else:
                        client_logger.error(f'Получено некорректное сообщение с сервера: {message}')


# Функция генерирует запрос о присутствии клиента
# @log
def create_presence(account_name):
    presence_message = {
        CONFIGS.get('ACTION'): CONFIGS.get('PRESENCE'),
        CONFIGS.get('TIME'): time.time(),
        CONFIGS.get('USER'): {
            CONFIGS.get('ACCOUNT_NAME'): account_name
        }
    }
    client_logger.debug(
        f'Сформировано {CONFIGS.get("PRESENCE")} сообщение для пользователя {account_name}: {presence_message}')
    return presence_message


# Функция разбирает ответ сервера на сообщение о присутствии,
# возращает 200 если все ОК или генерирует исключение при ошибке.
# @Log
def process_response_ans(message):
    client_logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if CONFIGS.get('RESPONSE') in message:
        if message[CONFIGS.get('RESPONSE')] == 200:
            return '200 : OK'
        elif message[CONFIGS.get('RESPONSE')] == 400:
            raise ServerError(f'400 : {message[CONFIGS.get("ERROR")]}')
    raise ReqFieldMissingError(CONFIGS.get('RESPONSE'))


# функция парсера аргументов командной строки
def arg_parser():
    # параметры командной строки скрипта client.py <addr> [<port>]:
    parser = argparse.ArgumentParser(description='command line client parameters')
    parser.add_argument('addr', type=str, nargs='?', default=CONFIGS.get('DEFAULT_IP_ADDRESS'),
                        help='server ip address')
    parser.add_argument('port', type=int, nargs='?', default=CONFIGS.get('DEFAULT_PORT'), help='port')
    parser.add_argument('-n', '--name', type=str, default=None, nargs='?', help='client name')
    args = parser.parse_args()
    # print(args)
    server_address = args.addr
    server_port = int(args.port)
    client_name = args.name

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        client_logger.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return server_address, server_port, client_name


# Функция запроса контакт листа
def contacts_list_request(sock, name):
    client_logger.debug(f'Запрос контакт листа для пользователя {name}')
    request = {
        CONFIGS.get('ACTION'): CONFIGS.get('GET_CONTACTS'),
        CONFIGS.get('TIME'): time.time(),
        CONFIGS.get('USER'): name
    }
    client_logger.debug(f'Сформирован запрос {request}')
    send_message(sock, request, CONFIGS)
    answer = get_message(sock, CONFIGS)
    client_logger.debug(f'Получен ответ {answer}')
    if CONFIGS.get('RESPONSE') in answer and answer[CONFIGS.get('RESPONSE')] == 202:
        return answer[CONFIGS.get('LIST_INFO')]
    else:
        raise ServerError


# Функция добавления пользователя в контакт лист
def add_contact(sock, username, contact):
    client_logger.debug(f'Создание контакта {contact}')
    request = {
        CONFIGS.get('ACTION'): CONFIGS.get('ADD_CONTACT'),
        CONFIGS.get('TIME'): time.time(),
        CONFIGS.get('USER'): username,
        CONFIGS.get('ACCOUNT_NAME'): contact
    }
    send_message(sock, request, CONFIGS)
    answer = get_message(sock, CONFIGS)
    if CONFIGS.get('RESPONSE') in answer and answer[CONFIGS.get('RESPONSE')] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    client_logger.debug(f'Запрос списка известных пользователей {username}')
    request = {
        CONFIGS.get('ACTION'): CONFIGS.get('USERS_REQUEST'),
        CONFIGS.get('TIME'): time.time(),
        CONFIGS.get('ACCOUNT_NAME'): username
    }
    send_message(sock, request, CONFIGS)
    answer = get_message(sock, CONFIGS)
    if CONFIGS.get('RESPONSE') in answer and answer[CONFIGS.get('RESPONSE')] == 202:
        return answer[CONFIGS.get('LIST_INFO')]
    else:
        raise ServerError


# Функция удаления пользователя из контакт листа
def remove_contact(sock, username, contact):
    client_logger.debug(f'Создание контакта {contact}')
    request = {
        CONFIGS.get('ACTION'): CONFIGS.get('REMOVE_CONTACT'),
        CONFIGS.get('TIME'): time.time(),
        CONFIGS.get('USER'): username,
        CONFIGS.get('ACCOUNT_NAME'): contact
    }
    send_message(sock, request, CONFIGS)
    answer = get_message(sock, CONFIGS)
    if CONFIGS.get('RESPONSE') in answer and answer[CONFIGS.get('RESPONSE')] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


# Функция инициализатор базы данных. Запускается при запуске, загружает данные в базу с сервера.
def database_load(sock, database, username):
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        client_logger.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        client_logger.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    # Сообщаем о запуске
    print('Консольный месседжер. Клиентский модуль.')

    # Загружаем параметы коммандной строки
    server_address, server_port, client_name = arg_parser()

    # Если имя пользователя не было задано, необходимо запросить пользователя.
    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    client_logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port}, '
        f'имя пользователя: {client_name}')

    # Инициализация сокета и сообщение серверу о нашем появлении
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут 1 секунда, необходим для освобождения сокета.
        transport.settimeout(1)

        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name), CONFIGS)
        answer = process_response_ans(get_message(transport, CONFIGS))
        client_logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        client_logger.error('Не удалось декодировать полученную Json строку.')
        exit(1)
    except ServerError as error:
        client_logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        exit(1)
    except ReqFieldMissingError as missing_error:
        client_logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        exit(1)
    except (ConnectionRefusedError, ConnectionError):
        client_logger.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        exit(1)
    else:
        # Инициализация БД
        database = ClientDatabase(client_name)
        database_load(transport, database, client_name)

        # Если соединение с сервером установлено корректно, запускаем поток взаимодействия с пользователем
        module_sender = ClientSender(client_name, transport, database)
        module_sender.daemon = True
        module_sender.start()
        client_logger.debug('Запущены процессы')

        # затем запускаем поток - приёмник сообщений.
        module_receiver = ClientReader(client_name, transport, database)
        module_receiver.daemon = True
        module_receiver.start()

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if module_receiver.is_alive() and module_sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
