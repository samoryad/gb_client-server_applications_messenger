import argparse
import configparser
import os
import select
import sys
import threading
import time
import socket

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.utils import get_configs, get_message, send_message
from log.server_log_config import server_logger
from log.log_decorator import log
from metaclasses import ServerVerifier
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from server_storage import ServerStorage
from server_descriptor import CheckPort

CONFIGS = get_configs()

# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()


@log()
# функция парсера аргументов командной строки
def arg_parser(default_port, default_address):
    # параметры командной строки скрипта server.py -p <port>, -a <addr>:
    parser = argparse.ArgumentParser(description='command line server parameters')
    parser.add_argument('-a', '--addr', type=str, default=default_address, help='ip address')
    parser.add_argument('-p', '--port', type=int, default=default_port, help='tcp-port')
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

        # список подключённых клиентов.
        self.clients = []

        # список сообщений на отправку.
        self.messages = []

        # словарь, содержащий сопоставленные имена и соответствующие им сокеты.
        self.client_names = dict()

        # конструктор предка
        super().__init__()

    def init_socket(self):
        server_logger.info(
            f'Запущен сервер, порт для подключений: {self.port} ,'
            f' адрес с которого принимаются подключения: {self.addr}.'
            f' Если адрес не указан, принимаются соединения с любых адресов.')

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

        # основной цикл программы сервера
        while True:
            # ждём подключения, если таймаут вышел, ловим исключение
            try:
                # принимает запрос на установку соединения
                client, addr = self.sock.accept()
            except OSError as e:
                pass  # timeout вышел
            else:
                server_logger.info(f'Установлено соединение с: {str(addr)}')
                # response = self.check_message_from_chat(get_message(client, CONFIGS), CONFIGS)
                # send_message(client, response, CONFIGS)
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 2)
            except OSError as err:
                server_logger.error(f'Ошибка работы с сокетами: {err}')

            # проверяем список клиентов, от которых нужно что-то прочитать
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    # print(f'клиент -------------- {client_with_message}')
                    # ловим от них сообщение и проверяем его на корректность и вносим в список
                    # сообщений messages (200 или 400)
                    try:
                        self.check_message_from_chat(get_message(client_with_message, CONFIGS), client_with_message, CONFIGS)
                        # self.messages.append(answer) - надо убирать из-за нового метода проверки
                        # print(messages)
                    except OSError:
                        # ищем клиента в словаре клиентов и удаляем его из базы подключённых
                        server_logger.info(
                            f'Клиент {client_with_message.getpeername()} отключился от сервера - r_list.')
                        for client_name in self.client_names:
                            if self.client_names[client_name] == client_with_message:
                                self.database.logout_user(client_name)
                                del self.client_names[client_name]
                                break
                        self.clients.remove(client_with_message)

            # если есть сообщения, обрабатываем каждое.
            for message in self.messages:
                try:
                    self.send_message_to_client(message, send_data_lst)
                except (ConnectionAbortedError, ConnectionError, ConnectionResetError, ConnectionRefusedError):
                    server_logger.info(
                        f'Связь с клиентом с именем {message[CONFIGS.get("TO_USER")]} была потеряна')
                    self.clients.remove(self.client_names[message[CONFIGS.get('TO_USER')]])
                    self.database.logout_user(message[CONFIGS.get('TO_USER')])
                    del self.client_names[message[CONFIGS.get('TO_USER')]]
            self.messages.clear()

    # метод адресной отправки сообщения определённому клиенту. Принимает словарь сообщение, список зарегистрированых
    # пользователей и слушающие сокеты. Ничего не возвращает.
    def send_message_to_client(self, message, listen_sockets):
        if message[CONFIGS.get('TO_USER')] in self.client_names and self.client_names[
            message[CONFIGS.get('TO_USER')]] in listen_sockets:
            send_message(self.client_names[message[CONFIGS.get('TO_USER')]], message, CONFIGS)
            server_logger.info(
                f'Отправлено сообщение пользователю {message[CONFIGS.get("TO_USER")]} '
                f'от пользователя {message[CONFIGS.get("FROM_USER")]}.')
        elif message[CONFIGS.get('TO_USER')] in self.client_names and self.client_names[
            message[CONFIGS.get('TO_USER')]] not in listen_sockets:
            raise ConnectionError
        else:
            server_logger.error(
                f'Пользователь {message[CONFIGS.get("TO_USER")]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    @log()
    # метод проверки сообщения клиента
    def check_message_from_chat(self, message, client, CONFIGS):
        global new_connection
        server_logger.debug(f'Обработка сообщения от клиента: {message}')

        # если это сообщение о присутствии, принимаем и отвечаем
        if CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'PRESENCE') and CONFIGS.get('TIME') in message and CONFIGS.get('USER') in message:
            # если такой пользователь ещё не зарегистрирован, регистрируем его,
            # иначе отправляем ответ и завершаем соединение.
            if message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')] not in self.client_names.keys():
                self.client_names[message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]] = client
                client_ip, client_port = client.getpeername()
                self.database.login_user(
                    message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')], client_ip, client_port)
                send_message(client, {
                    CONFIGS.get('RESPONSE'): 200
                }, CONFIGS)
                with conflag_lock:
                    new_connection = True
            else:
                send_message(client, {
                    CONFIGS.get('RESPONSE'): 400,
                    CONFIGS.get('ERROR'): 'This name already taken'
                }, CONFIGS)
                self.clients.remove(client)
                client.close()
            return
        # {'action': 'message', 'from': 'test1', 'to': 'test2', 'time': 1616711690.8860502, 'message_text': 'gggggggggggggg'}

        # если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'MESSAGE') and CONFIGS.get('TO_USER') in message and CONFIGS.get('TIME') in message and CONFIGS.get(
            'FROM_USER') in message and CONFIGS.get('MESSAGE_TEXT') in message and self.client_names[
            message[CONFIGS.get('FROM_USER')]] == client:
            self.messages.append(message)
            self.database.process_message(
                message[CONFIGS.get('FROM_USER')], message[CONFIGS.get('TO_USER')])
            return

        # если клиент выходит
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get('EXIT') and CONFIGS.get(
                'ACCOUNT_NAME') in message and self.client_names[message[CONFIGS.get('ACCOUNT_NAME')]] == client:
            self.database.logout_user(message[CONFIGS.get('ACCOUNT_NAME')])
            server_logger.info(
                f'Клиент {message[CONFIGS.get("ACCOUNT_NAME")]} корректно отключился от сервера.')
            self.clients.remove(self.client_names[message[CONFIGS.get("ACCOUNT_NAME")]])
            self.client_names[message[CONFIGS.get("ACCOUNT_NAME")]].close()
            del self.client_names[message[CONFIGS.get("ACCOUNT_NAME")]]
            with conflag_lock:
                new_connection = True
            return

        # если это запрос контакт-листа
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'GET_CONTACTS') and CONFIGS.get('USER') in message and self.client_names[
            message[CONFIGS.get('USER')]] == client:
            response = {
                CONFIGS.get('RESPONSE'): 202,
                CONFIGS.get('LIST_INFO'): self.database.get_contacts(message[CONFIGS.get('USER')])
            }
            send_message(client, response, CONFIGS)

        # если это добавление контакта
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'ADD_CONTACT') and CONFIGS.get("ACCOUNT_NAME") in message and CONFIGS.get('USER') in message and \
                self.client_names[message[CONFIGS.get('USER')]] == client:
            self.database.add_contact(message[CONFIGS.get('USER')], message[CONFIGS.get("ACCOUNT_NAME")])
            send_message(client, {CONFIGS.get('RESPONSE'): 200}, CONFIGS)

        # если это удаление контакта
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'REMOVE_CONTACT') and CONFIGS.get('ACCOUNT_NAME') in message and CONFIGS.get('USER') in message and \
                self.client_names[message[CONFIGS.get('USER')]] == client:
            self.database.remove_contact(message[CONFIGS.get('USER')], message[CONFIGS.get('ACCOUNT_NAME')])
            send_message(client, {CONFIGS.get('RESPONSE'): 200}, CONFIGS)

        # если это запрос известных пользователей
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'USERS_REQUEST') and CONFIGS.get('ACCOUNT_NAME') in message and self.client_names[
            message[CONFIGS.get('ACCOUNT_NAME')]] == client:
            response = {
                CONFIGS.get('RESPONSE'): 202,
                CONFIGS.get('LIST_INFO'): [user[0] for user in self.database.all_users_list()]
            }
            send_message(client, response, CONFIGS)

        # иначе отдаём Bad request
        else:
            send_message(client, {
                CONFIGS.get('RESPONSE'): 400,
                CONFIGS.get('ERROR'): 'Not correct request'
            }, CONFIGS)
            return


def print_help():
    print('Поддерживаемые комманды:')
    print('all_users - список известных пользователей')
    print('active - список подключенных пользователей')
    print('login_history - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    # Загрузка файла конфигурации сервера
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")

    # Загрузка параметров командной строки, если нет параметров, то задаём
    # значения по умоланию.
    listen_address, listen_port = arg_parser(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    # Инициализация базы данных
    database = ServerStorage()

    # Создание экземпляра класса - сервера и его запуск:
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Создаём графическое окуружение для сервера:
    server_app = QApplication(sys.argv)
    # главное окно
    main_window = MainWindow()

    # Инициализируем параметры в окна
    # надпись в статус баре
    main_window.statusBar().showMessage('Server Working')
    # список активных пользователей (автоподбор размера колонки)
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция обновляющяя список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Функция создающяя окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


    # # Загрузка файла конфигурации сервера
    # config = configparser.ConfigParser()
    #
    # dir_path = os.path.dirname(os.path.realpath(__file__))
    # config.read(f"{dir_path}/{'server.ini'}")
    #
    # # грузим парамтры командной строки
    # listen_address, listen_port = arg_parser()
    #
    # # создаём экземпляр базы данных
    # database = ServerStorage()
    #
    # # создаём экземпляр класса сервер
    # server = Server(listen_address, listen_port, database)
    # server.daemon = True
    # server.start()
    #
    # # Создаём графическое окуружение для сервера:
    # server_app = QApplication(sys.argv)
    # main_window = MainWindow()
    #
    # # Инициализируем параметры в окна
    # main_window.statusBar().showMessage('Server Working')
    # main_window.active_clients_table.setModel(gui_create_model(database))
    # main_window.active_clients_table.resizeColumnsToContents()
    # main_window.active_clients_table.resizeRowsToContents()
    #
    # # Функция обновляющяя список подключённых, проверяет флаг подключения, и
    # # если надо обновляет список
    # def list_update():
    #     global new_connection
    #     if new_connection:
    #         main_window.active_clients_table.setModel(
    #             gui_create_model(database))
    #         main_window.active_clients_table.resizeColumnsToContents()
    #         main_window.active_clients_table.resizeRowsToContents()
    #         with conflag_lock:
    #             new_connection = False
    #
    # # печатаем справку
    # print_help()
    #
    # # основной цикл сервера
    # while True:
    #     command = input('Введите комманду: ')
    #     if command == 'help':
    #         print_help()
    #     elif command == 'exit':
    #         break
    #     elif command == 'all_users':
    #         for user in sorted(database.all_users_list()):
    #             print(f'Пользователь {user[0]}, последний вход: {user[1]}')
    #     elif command == 'active':
    #         for user in sorted(database.active_users_list()):
    #             print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
    #     elif command == 'login_history':
    #         for user in sorted(database.login_history()):
    #             print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
    #     else:
    #         print('Команда не распознана.')


if __name__ == '__main__':
    print('Стартуем сервер')
    main()
