import binascii
import hmac
import json
import os
import select
import threading
import socket
from common.utils import get_configs, get_message, send_message
from log.log_decorator import log
from log.server_log_config import server_logger
from server_descriptor import CheckPort

CONFIGS = get_configs()

# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()


class MessageProcessor(threading.Thread):
    # """класс сервера"""
    listen_port = CheckPort()

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
        self.client_names = dict()

        # конструктор предка
        super().__init__()

    def run(self):
        '''Метод - основной цикл потока.'''
        # инициализируем сокет
        self.init_socket()

        # основной цикл программы сервера
        while self.running:
            # ждём подключения, если таймаут вышел, ловим исключение
            try:
                # принимает запрос на установку соединения
                client, addr = self.sock.accept()
            except OSError:
                pass  # timeout вышел
            else:
                server_logger.info(f'Установлено соединение с: {str(addr)}')
                client.settimeout(5)
                self.clients.append(client)

            recv_data_lst = []
            # проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = select.select(self.clients, self.clients,
                                                                                           [], 2)
            except OSError as err:
                server_logger.error(f'Ошибка работы с сокетами: {err.errno}')

            # принимаем сообщения и если ошибка, исключаем клиента
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    # ловим от них сообщение и проверяем его на корректность и вносим в список
                    # сообщений messages (200 или 400)
                    try:
                        self.check_message_from_chat(get_message(client_with_message, CONFIGS), client_with_message,
                                                     CONFIGS)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        # ищем клиента в словаре клиентов и удаляем его из базы подключённых
                        server_logger.debug(f'Получение данных из исключения клиента', exc_info=err)
                        self.remove_client(client_with_message)

    def remove_client(self, client):
        '''
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        '''
        server_logger.info(
            f'Клиент {client.getpeername()} отключился от сервера')
        for client_name in self.client_names:
            if self.client_names[client_name] == client:
                self.database.logout_user(client_name)
                del self.client_names[client_name]
                break
        self.clients.remove(client)
        client.close()

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

    # метод адресной отправки сообщения определённому клиенту. Принимает словарь сообщение, список зарегистрированых
    # пользователей и слушающие сокеты. Ничего не возвращает.
    @log()
    def send_message_to_client(self, message):
        '''
        Метод отправки сообщения клиенту.
        '''
        if message[CONFIGS.get('TO_USER')] in self.client_names and self.client_names[
            message[CONFIGS.get('TO_USER')]] in self.listen_sockets:
            try:
                send_message(self.client_names[message[CONFIGS.get('TO_USER')]], message, CONFIGS)
                server_logger.info(
                    f'Отправлено сообщение пользователю {message[CONFIGS.get("TO_USER")]} '
                    f'от пользователя {message[CONFIGS.get("FROM_USER")]}.')
            except OSError:
                self.remove_client(message[CONFIGS.get('TO_USER')])
        elif message[CONFIGS.get('TO_USER')] in self.client_names and self.client_names[
            message[CONFIGS.get('TO_USER')]] not in self.listen_sockets:
            server_logger.error(
                f'Связь с клиентом {message[CONFIGS.get("TO_USER")]} была потеряна. '
                f'Соединение закрыто, доставка невозможна.')
            self.remove_client(self.client_names[message[CONFIGS.get('TO_USER')]])
        else:
            server_logger.error(
                f'Пользователь {message[CONFIGS.get("TO_USER")]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    @log()
    # метод проверки сообщения клиента
    def check_message_from_chat(self, message, client, CONFIGS):
        '''Метод - отбработчик поступающих сообщений.'''
        server_logger.debug(f'Обработка сообщения от клиента: {message}')

        # если это сообщение о присутствии, принимаем и отвечаем
        if CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'PRESENCE') and CONFIGS.get('TIME') in message and CONFIGS.get('USER') in message:
            # Если сообщение о присутствии то вызываем функцию авторизации.
            self.autorize_user(message, client)

        # Если это сообщение, то отправляем его получателю.
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'MESSAGE') and CONFIGS.get('TO_USER') in message and CONFIGS.get('TIME') in message and CONFIGS.get(
            'FROM_USER') in message and CONFIGS.get('MESSAGE_TEXT') in message and self.client_names[
            message[CONFIGS.get('FROM_USER')]] == client:
            if message[CONFIGS.get('TO_USER')] in self.client_names:
                self.database.process_message(
                    message[CONFIGS.get('FROM_USER')], message[CONFIGS.get('TO_USER')])
                self.send_message_to_client(message)
                try:
                    send_message(client, {CONFIGS.get('RESPONSE'): 200}, CONFIGS)
                except OSError:
                    self.remove_client(client)
            else:
                try:
                    send_message(client, {
                        CONFIGS.get('RESPONSE'): 400,
                        CONFIGS.get('ERROR'): 'User is not registered on server.'
                    }, CONFIGS)
                except OSError:
                    pass
            return

        # если клиент выходит
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get('EXIT') and CONFIGS.get(
                'ACCOUNT_NAME') in message and self.client_names[message[CONFIGS.get('ACCOUNT_NAME')]] == client:
            self.remove_client(client)

        # если это запрос контакт-листа
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'GET_CONTACTS') and CONFIGS.get('USER') in message and self.client_names[
            message[CONFIGS.get('USER')]] == client:
            response = {
                CONFIGS.get('RESPONSE'): 202,
                CONFIGS.get('LIST_INFO'): self.database.get_contacts(message[CONFIGS.get('USER')])
            }
            try:
                send_message(client, response, CONFIGS)
            except OSError:
                self.remove_client(client)

        # если это добавление контакта
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'ADD_CONTACT') and CONFIGS.get("ACCOUNT_NAME") in message and CONFIGS.get('USER') in message and \
                self.client_names[message[CONFIGS.get('USER')]] == client:
            self.database.add_contact(message[CONFIGS.get('USER')], message[CONFIGS.get("ACCOUNT_NAME")])
            try:
                send_message(client, {CONFIGS.get('RESPONSE'): 200}, CONFIGS)
            except OSError:
                self.remove_client(client)

        # если это удаление контакта
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'REMOVE_CONTACT') and CONFIGS.get('ACCOUNT_NAME') in message and CONFIGS.get('USER') in message and \
                self.client_names[message[CONFIGS.get('USER')]] == client:
            self.database.remove_contact(message[CONFIGS.get('USER')], message[CONFIGS.get('ACCOUNT_NAME')])
            try:
                send_message(client, {CONFIGS.get('RESPONSE'): 200}, CONFIGS)
            except OSError:
                self.remove_client(client)

        # если это запрос известных пользователей
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'USERS_REQUEST') and CONFIGS.get('ACCOUNT_NAME') in message and self.client_names[
            message[CONFIGS.get('ACCOUNT_NAME')]] == client:
            response = {
                CONFIGS.get('RESPONSE'): 202,
                CONFIGS.get('LIST_INFO'): [user[0] for user in self.database.all_users_list()]
            }
            try:
                send_message(client, response, CONFIGS)
            except OSError:
                self.remove_client(client)

        # Если это запрос публичного ключа пользователя
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'PUBLIC_KEY_REQUEST') and CONFIGS.get('ACCOUNT_NAME') in message:
            response = {
                CONFIGS.get('RESPONSE'): 511,
                CONFIGS.get('DATA'): None
            }
            response[CONFIGS.get('DATA')] = self.database.get_pubkey(message[CONFIGS.get('ACCOUNT_NAME')])
            # может быть, что ключа ещё нет (пользователь никогда не логинился,
            # тогда шлём 400)
            if response[CONFIGS.get('DATA')]:
                try:
                    send_message(client, response, CONFIGS)
                except OSError:
                    self.remove_client(client)
            else:
                try:
                    send_message(client, {
                        CONFIGS.get('RESPONSE'): 400,
                        CONFIGS.get('ERROR'): 'There is no public key for this user'
                    }, CONFIGS)
                except OSError:
                    self.remove_client(client)

        # иначе отдаём Bad request
        else:
            try:
                send_message(client, {
                    CONFIGS.get('RESPONSE'): 400,
                    CONFIGS.get('ERROR'): 'Not correct request'
                }, CONFIGS)
            except OSError:
                self.remove_client(client)

    def autorize_user(self, message, sock):
        '''Метод реализующий авторизцию пользователей.'''

        # Если имя пользователя уже занято то возвращаем 400
        server_logger.debug(f'Start auth process for {message[CONFIGS.get("USER")]}')
        if message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')] in self.client_names.keys():
            response = {
                CONFIGS.get('RESPONSE'): 400,
                CONFIGS.get('ERROR'): 'The username is already taken'
            }
            try:
                server_logger.debug(f'Username busy, sending {response}')
                send_message(sock, response, CONFIGS)
            except OSError:
                server_logger.debug('OS Error')
                pass
            self.clients.remove(sock)
            sock.close()

        # Проверяем что пользователь зарегистрирован на сервере.
        elif not self.database.check_user(message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]):
            response = {
                CONFIGS.get('RESPONSE'): 400,
                CONFIGS.get('ERROR'): 'The user is not registered'
            }
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
            message_auth = {
                CONFIGS.get('RESPONSE'): 511,
                CONFIGS.get('DATA'): None
            }
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[CONFIGS.get('DATA')] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем серверную версию ключа
            hash = hmac.new(self.database.get_hash(message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]),
                            random_str, 'MD5')
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
            # Если ответ клиента корректный, то сохраняем его в список пользователей.
            if CONFIGS.get('RESPONSE') in ans and ans[CONFIGS.get('RESPONSE')] == 511 and hmac.compare_digest(
                    digest, client_digest):
                self.client_names[message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, {CONFIGS.get('RESPONSE'): 200}, CONFIGS)
                except OSError:
                    self.remove_client(message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')])
                # добавляем пользователя в список активных и если у него изменился открытый ключ сохраняем новый
                self.database.login_user(
                    message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')],
                    client_ip,
                    client_port,
                    message[CONFIGS.get('USER')][CONFIGS.get('PUBLIC_KEY')])
            else:
                response = {
                    CONFIGS.get('RESPONSE'): 400,
                    CONFIGS.get('ERROR'): 'Wrong password'
                }
                try:
                    send_message(sock, response, CONFIGS)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        '''Метод реализующий отправки сервисного сообщения 205 клиентам.'''
        for client in self.client_names:
            try:
                send_message(self.client_names[client], {CONFIGS.get('RESPONSE'): 205}, CONFIGS)
            except OSError:
                self.remove_client(self.client_names[client])
