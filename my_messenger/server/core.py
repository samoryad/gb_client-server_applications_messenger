import binascii
import hmac
import json
import os
import select
import threading
import socket

from my_messenger.common.answers import RESPONSE_200, RESPONSE_400, \
    RESPONSE_202, RESPONSE_511, RESPONSE_205
from my_messenger.common.decorators import login_required
from my_messenger.common.descryptors import Port
from my_messenger.common.utils import get_configs, get_message, send_message
from my_messenger.common.decorators import log
from my_messenger.log.server_log_config import server_logger

CONFIGS = get_configs()


class MessageProcessor(threading.Thread):
    """
    Основной класс сервера. Принимает содинения, словари - пакеты
    от клиентов, обрабатывает поступающие сообщения.
    Работает в качестве отдельного потока.
    """
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        # параментры подключения
        self.addr = listen_address
        self.port = listen_port

        # база данных сервера
        self.database = database

        # Сокет, через который будет осуществляться работа
        self.sock = None

        # список подключённых клиентов.
        self.clients = []

        # Сокеты
        self.listen_sockets = None
        self.error_sockets = None

        # Флаг продолжения работы
        self.running = True

        # словарь, содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

        # конструктор предка
        super().__init__()

    def run(self):
        """Метод - основной цикл потока."""
        # инициализируем сокет
        self.init_socket()

        # основной цикл программы сервера
        while self.running:
            # ждём подключения, если таймаут вышел, ловим исключение
            try:
                # принимает запрос на установку соединения
                client, client_address = self.sock.accept()
            except OSError:
                pass  # timeout вышел
            else:
                server_logger.info(
                    f'Установлено соединение с: {str(client_address)}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = \
                        select.select(self.clients, self.clients, [], 0)
            except OSError as err:
                server_logger.error(f'Ошибка работы с сокетами: {err.errno}')

            # принимаем сообщения и если ошибка, исключаем клиента
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(
                            get_message(
                                client_with_message,
                                CONFIGS),
                            client_with_message,
                            CONFIGS)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        server_logger.debug(
                            f'Getting data from client exception',
                            exc_info=err
                        )
                        self.remove_client(client_with_message)

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        """
        server_logger.info(
            f'Клиент {client.getpeername()} отключился от сервера')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def init_socket(self):
        """Метод инициализатор сокета."""
        server_logger.info(
            f'Запущен сервер, порт для подключений: {self.port} ,'
            f' адрес с которого принимаются подключения: {self.addr}.'
            f' Если адрес не указан, принимаются соединения с любых адресов.')

        # сервер создаёт сокет
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # привязывает сокет к IP-адресу и порту машины
        transport.bind((self.addr, self.port))
        # Таймаут для операций с сокетом (0.5 секунды)
        transport.settimeout(0.5)

        self.sock = transport
        # готов принимать соединения
        self.sock.listen(CONFIGS.get('MAX_CONNECTIONS'))

    @log
    def process_message(self, message):
        """
        Метод отправки сообщения клиенту.
        """
        if message[CONFIGS.get('TO_USER')] in self.names and self.names[
                message[CONFIGS.get('TO_USER')]] in self.listen_sockets:
            try:
                send_message(
                    self.names[message[CONFIGS.get('TO_USER')]],
                    message,
                    CONFIGS
                )
                server_logger.info(
                    f'Отправлено сообщение пользователю '
                    f'{message[CONFIGS.get("TO_USER")]} '
                    f'от пользователя {message[CONFIGS.get("FROM_USER")]}.')
            except OSError:
                self.remove_client(message[CONFIGS.get('TO_USER')])
        elif message[CONFIGS.get('TO_USER')] in self.names and self.names[
                message[CONFIGS.get('TO_USER')]] not in self.listen_sockets:
            server_logger.error(
                f'Связь с клиентом {message[CONFIGS.get("TO_USER")]} '
                f'была потеряна. '
                f'Соединение закрыто, доставка невозможна.')
            self.remove_client(self.names[message[CONFIGS.get('TO_USER')]])
        else:
            server_logger.error(
                f'Пользователь {message[CONFIGS.get("TO_USER")]} '
                f'не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    @login_required
    # метод проверки сообщения клиента
    def process_client_message(self, message, client, CONFIGS):
        """Метод - отбработчик поступающих сообщений."""
        server_logger.debug(f'Обработка сообщения от клиента: {message}')

        # если это сообщение о присутствии, принимаем и отвечаем
        if CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == CONFIGS.get('PRESENCE') and \
                CONFIGS.get('TIME') in message and \
                CONFIGS.get('USER') in message:
            # Если сообщение о присутствии то вызываем функцию авторизации.
            self.authorize_user(message, client)

        # Если это сообщение, то отправляем его получателю.
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == CONFIGS.get('MESSAGE') and \
                CONFIGS.get('TO_USER') in message and \
                CONFIGS.get('TIME') in message and \
                CONFIGS.get('FROM_USER') in message and \
                CONFIGS.get('MESSAGE_TEXT') in message and \
                self.names[message[CONFIGS.get('FROM_USER')]] == client:
            if message[CONFIGS.get('TO_USER')] in self.names:
                self.database.process_message(message[CONFIGS.get(
                    'FROM_USER')], message[CONFIGS.get('TO_USER')])
                self.process_message(message)
                try:
                    send_message(client, RESPONSE_200, CONFIGS)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[CONFIGS.get(
                    'ERROR')] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    send_message(client, response, CONFIGS)
                except OSError:
                    pass
            return

        # если клиент выходит
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == CONFIGS.get('EXIT') and \
                CONFIGS.get('ACCOUNT_NAME') in message and \
                self.names[message[CONFIGS.get('ACCOUNT_NAME')]] == client:
            self.remove_client(client)

        # если это запрос контакт-листа
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == CONFIGS.get('GET_CONTACTS') \
                and CONFIGS.get('USER') in message and \
                self.names[message[CONFIGS.get('USER')]] == client:
            response = RESPONSE_202
            response[CONFIGS.get('LIST_INFO')] = self.database.get_contacts(
                message[CONFIGS.get('USER')])
            try:
                send_message(client, response, CONFIGS)
            except OSError:
                self.remove_client(client)

        # если это добавление контакта
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == CONFIGS.get('ADD_CONTACT') \
                and CONFIGS.get("ACCOUNT_NAME") in message and \
                CONFIGS.get('USER') in message and \
                self.names[message[CONFIGS.get('USER')]] == client:
            self.database.add_contact(message[CONFIGS.get(
                'USER')], message[CONFIGS.get("ACCOUNT_NAME")])
            try:
                send_message(client, RESPONSE_200, CONFIGS)
            except OSError:
                self.remove_client(client)

        # если это удаление контакта
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == \
                CONFIGS.get('REMOVE_CONTACT') and \
                CONFIGS.get('ACCOUNT_NAME') in message and \
                CONFIGS.get('USER') in message and \
                self.names[message[CONFIGS.get('USER')]] == client:
            self.database.remove_contact(message[CONFIGS.get(
                'USER')], message[CONFIGS.get('ACCOUNT_NAME')])
            try:
                send_message(client, RESPONSE_200, CONFIGS)
            except OSError:
                self.remove_client(client)

        # если это запрос известных пользователей
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == CONFIGS.get('USERS_REQUEST')\
                and CONFIGS.get('ACCOUNT_NAME') in message and \
                self.names[message[CONFIGS.get('ACCOUNT_NAME')]] == client:
            response = RESPONSE_202
            response[CONFIGS.get('LIST_INFO')] = \
                [user[0] for user in self.database.users_list()]
            try:
                send_message(client, response, CONFIGS)
            except OSError:
                self.remove_client(client)

        # Если это запрос публичного ключа пользователя
        elif CONFIGS.get('ACTION') in message and \
                message[CONFIGS.get('ACTION')] == \
                CONFIGS.get('PUBLIC_KEY_REQUEST') and \
                CONFIGS.get('ACCOUNT_NAME') in message:
            response = RESPONSE_511
            response[CONFIGS.get('DATA')] = self.database.get_pubkey(
                message[CONFIGS.get('ACCOUNT_NAME')])
            # может быть, что ключа ещё нет (пользователь никогда не логинился,
            # тогда шлём 400)
            if response[CONFIGS.get('DATA')]:
                try:
                    send_message(client, response, CONFIGS)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[CONFIGS.get('ERROR')] = \
                    'Нет публичного ключа для данного пользователя'
                try:
                    send_message(client, response, CONFIGS)
                except OSError:
                    self.remove_client(client)

        # иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[CONFIGS.get('ERROR')] = 'Запрос некорректен.'
            try:
                send_message(client, response, CONFIGS)
            except OSError:
                self.remove_client(client)

    def authorize_user(self, message, sock):
        """Метод реализующий авторизцию пользователей."""
        # Если имя пользователя уже занято то возвращаем 400
        server_logger.debug(
            f'Start auth process for {message[CONFIGS.get("USER")]}')
        if message[CONFIGS.get('USER')][CONFIGS.get(
                'ACCOUNT_NAME')] in self.names.keys():
            response = RESPONSE_400
            response[CONFIGS.get('ERROR')] = 'Имя пользователя уже занято.'
            try:
                server_logger.debug(f'Username busy, sending {response}')
                send_message(sock, response, CONFIGS)
            except OSError:
                server_logger.debug('OS Error')
                pass
            self.clients.remove(sock)
            sock.close()

        # Проверяем что пользователь зарегистрирован на сервере.
        elif not self.database.check_user(message[CONFIGS.get('USER')]
                                          [CONFIGS.get('ACCOUNT_NAME')]):
            response = RESPONSE_400
            response[CONFIGS.get('ERROR')] = 'Пользователь не зарегистрирован.'
            try:
                server_logger.debug(f'Unknown username, sending {response}')
                send_message(sock, response, CONFIGS)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            server_logger.debug('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            # Словарь - заготовка
            message_auth = RESPONSE_511
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[CONFIGS.get('DATA')] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем
            # серверную версию ключа
            hash = hmac.new(self.database.get_hash(message[CONFIGS.get(
                'USER')][CONFIGS.get('ACCOUNT_NAME')]), random_str, 'MD5')
            digest = hash.digest()
            server_logger.debug(f'Auth message = {message_auth}')
            try:
                # Обмен с клиентом
                send_message(sock, message_auth, CONFIGS)
                ans = get_message(sock, CONFIGS)
            except OSError as err:
                server_logger.debug('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[CONFIGS.get('DATA')])
            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.
            if CONFIGS.get('RESPONSE') in ans and \
                    ans[CONFIGS.get('RESPONSE')] == 511 and \
                    hmac.compare_digest(digest, client_digest):
                self.names[message[CONFIGS.get(
                    'USER')][CONFIGS.get('ACCOUNT_NAME')]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200, CONFIGS)
                except OSError:
                    self.remove_client(message[CONFIGS.get(
                        'USER')][CONFIGS.get('ACCOUNT_NAME')])
                # добавляем пользователя в список активных и если у него
                # изменился открытый ключ сохраняем новый
                self.database.user_login(
                    message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')],
                    client_ip,
                    client_port,
                    message[CONFIGS.get('USER')][CONFIGS.get('PUBLIC_KEY')])
            else:
                response = RESPONSE_400
                response[CONFIGS.get('ERROR')] = 'Неверный пароль.'
                try:
                    send_message(sock, response, CONFIGS)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        """Метод реализующий отправки сервисного сообщения 205 клиентам."""
        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205, CONFIGS)
            except OSError:
                self.remove_client(self.names[client])
