import binascii
import hashlib
import hmac
import json
import socket
import time
import threading
from PyQt5.QtCore import pyqtSignal, QObject

from my_messenger.common.answers import RESPONSE_511
from my_messenger.common.decorators import Log
from my_messenger.common.errors import ServerError
from my_messenger.common.utils import get_configs, send_message, get_message
from my_messenger.log.client_log_config import client_logger

CONFIGS = get_configs()

# объект блокировки для работы с сокетом.
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    """
    Класс реализующий транспортную подсистему клиентского
    модуля. Отвечает за взаимодействие с сервером.
    """
    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(dict)
    message_205 = pyqtSignal()
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username, passwd, keys):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database = database

        # Имя пользователя
        self.username = username

        # Пароль
        self.password = passwd

        # Сокет для работы с сервером
        self.transport = None

        # Набор ключей для шифрования
        self.keys = keys

        # Устанавливаем соединение:
        self.connection_init(port, ip_address)

        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                client_logger.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            client_logger.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            client_logger.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
            # Флаг продолжения работы транспорта.
        self.running = True

    def connection_init(self, port, ip):
        """Метод отвечающий за устанновку соединения с сервером."""
        # Инициализация сокета и сообщение серверу о нашем появлении
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут необходим для освобождения сокета.
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            client_logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                client_logger.debug("Connection established.")
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            client_logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        client_logger.debug('Starting auth dialog.')

        # Запускаем процедуру авторизации
        # Получаем хэш пароля
        passwd_bytes = self.password.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        passwd_hash_string = binascii.hexlify(passwd_hash)

        client_logger.debug(f'Passwd hash ready: {passwd_hash_string}')

        # Получаем публичный ключ и декодируем его из байтов
        pubkey = self.keys.publickey().export_key().decode('ascii')

        # Авторизируемся на сервере
        with socket_lock:
            presense = {
                CONFIGS.get('ACTION'): CONFIGS.get('PRESENCE'),
                CONFIGS.get('TIME'): time.time(),
                CONFIGS.get('USER'): {
                CONFIGS.get('ACCOUNT_NAME'): self.username,
                    CONFIGS.get('PUBLIC_KEY'): pubkey
                }
            }
            client_logger.debug(f"Presence message = {presense}")
            # Отправляем серверу приветственное сообщение.
            try:
                send_message(self.transport, presense, CONFIGS)
                ans = get_message(self.transport, CONFIGS)
                client_logger.debug(f'Server response = {ans}.')
                # Если сервер вернул ошибку, бросаем исключение.
                if CONFIGS.get('RESPONSE') in ans:
                    if ans[CONFIGS.get('RESPONSE')] == 400:
                        raise ServerError(ans[CONFIGS.get('ERROR')])
                    elif ans[CONFIGS.get('RESPONSE')] == 511:
                        # Если всё нормально, то продолжаем процедуру
                        # авторизации.
                        ans_data = ans[CONFIGS.get('DATA')]
                        hash = hmac.new(passwd_hash_string, ans_data.encode('utf-8'), 'MD5')
                        digest = hash.digest()
                        my_ans = RESPONSE_511
                        my_ans[CONFIGS.get('DATA')] = binascii.b2a_base64(
                            digest).decode('ascii')
                        send_message(self.transport, my_ans, CONFIGS)
                        self.process_server_ans(get_message(self.transport, CONFIGS))
            except (OSError, json.JSONDecodeError) as err:
                client_logger.debug(f'Connection error.', exc_info=err)
                raise ServerError('Сбой соединения в процессе авторизации.')

    @Log()
    def process_server_ans(self, message):
        """Метод обработчик поступающих сообщений с сервера."""
        client_logger.debug(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if CONFIGS.get('RESPONSE') in message:
            if message[CONFIGS.get('RESPONSE')] == 200:
                return
            elif message[CONFIGS.get('RESPONSE')] == 400:
                raise ServerError(f'{message[CONFIGS.get("ERROR")]}')
            elif message[CONFIGS.get('RESPONSE')] == 205:
                self.user_list_update()
                self.contacts_list_update()
                self.message_205.emit()
            else:
                client_logger.debug(f'Принят неизвестный код подтверждения {CONFIGS.get("RESPONSE")}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get(
                'MESSAGE') and CONFIGS.get('FROM_USER') in message and CONFIGS.get(
            'TO_USER') in message and CONFIGS.get('MESSAGE_TEXT') in message and message[
                CONFIGS.get('TO_USER')] == self.username:
            client_logger.debug(
                f'Получено сообщение от пользователя {message[CONFIGS.get("FROM_USER")]}:'
                f'{message[CONFIGS.get("MESSAGE_TEXT")]}')
            self.new_message.emit(message)

    def contacts_list_update(self):
        """Метод обновляющий с сервера список контактов."""
        self.database.contacts_clear()
        client_logger.debug(f'Запрос контакт листа для пользователся {self.name}')
        req = {
            CONFIGS.get('ACTION'): CONFIGS.get('GET_CONTACTS'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS.get('USER'): self.username
        }
        client_logger.debug(f'Сформирован запрос {req}')
        with socket_lock:
            send_message(self.transport, req, CONFIGS)
            ans = get_message(self.transport, CONFIGS)
        client_logger.debug(f'Получен ответ {ans}')
        if CONFIGS.get('RESPONSE') in ans and ans[CONFIGS.get('RESPONSE')] == 202:
            for contact in ans[CONFIGS.get('LIST_INFO')]:
                self.database.add_contact(contact)
        else:
            client_logger.error('Не удалось обновить список контактов.')

    def user_list_update(self):
        """Метод обновляющий с сервера список пользователей."""
        client_logger.debug(f'Запрос списка известных пользователей {self.username}')
        req = {
            CONFIGS.get('ACTION'): CONFIGS.get('USERS_REQUEST'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS.get('ACCOUNT_NAME'): self.username
        }
        with socket_lock:
            send_message(self.transport, req, CONFIGS)
            ans = get_message(self.transport, CONFIGS)
        if CONFIGS.get('RESPONSE') in ans and ans[CONFIGS.get('RESPONSE')] == 202:
            self.database.add_users(ans[CONFIGS.get('LIST_INFO')])
        else:
            client_logger.error('Не удалось обновить список известных пользователей.')

    def key_request(self, user):
        """Метод запрашивающий с сервера публичный ключ пользователя."""
        client_logger.debug(f'Запрос публичного ключа для {user}')
        req = {
            CONFIGS.get('ACTION'): CONFIGS.get('PUBLIC_KEY_REQUEST'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS.get('ACCOUNT_NAME'): user
        }
        with socket_lock:
            send_message(self.transport, req, CONFIGS)
            ans = get_message(self.transport, CONFIGS)
        if CONFIGS.get('RESPONSE') in ans and ans[CONFIGS.get('RESPONSE')] == 511:
            return ans[CONFIGS.get('DATA')]
        else:
            client_logger.error(f'Не удалось получить ключ собеседника{user}.')

    def add_contact(self, contact):
        """Метод отправляющий на сервер сведения о добавлении контакта."""
        client_logger.debug(f'Создание контакта {contact}')
        req = {
            CONFIGS.get('ACTION'): CONFIGS.get('ADD_CONTACT'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS.get('USER'): self.username,
            CONFIGS.get('ACCOUNT_NAME'): contact
        }
        with socket_lock:
            send_message(self.transport, req, CONFIGS)
            self.process_server_ans(get_message(self.transport, CONFIGS))

    def remove_contact(self, contact):
        """Метод отправляющий на сервер сведения о удалении контакта."""
        client_logger.debug(f'Удаление контакта {contact}')
        req = {
            CONFIGS.get('ACTION'): CONFIGS.get('REMOVE_CONTACT'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS.get('USER'): self.username,
            CONFIGS.get('ACCOUNT_NAME'): contact
        }
        with socket_lock:
            send_message(self.transport, req, CONFIGS)
            self.process_server_ans(get_message(self.transport, CONFIGS))

    def transport_shutdown(self):
        """Метод уведомляющий сервер о завершении работы клиента."""
        self.running = False
        message = {
            CONFIGS.get('ACTION'): CONFIGS.get('EXIT'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS['ACCOUNT_NAME']: self.username
        }
        with socket_lock:
            try:
                send_message(self.transport, message, CONFIGS)
            except OSError:
                pass
        client_logger.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    def send_message(self, to, message):
        """Метод отправляющий на сервер сообщения для пользователя."""
        message_dict = {
            CONFIGS['ACTION']: CONFIGS['MESSAGE'],
            CONFIGS['FROM_USER']: self.username,
            CONFIGS['TO_USER']: to,
            CONFIGS['TIME']: time.time(),
            CONFIGS['MESSAGE_TEXT']: message
        }
        client_logger.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            send_message(self.transport, message_dict, CONFIGS)
            self.process_server_ans(get_message(self.transport, CONFIGS))
            client_logger.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        """Метод содержащий основной цикл работы транспортного потока."""
        client_logger.debug('Запущен процесс - приёмник собщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            message = None
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport, CONFIGS)
                except OSError as err:
                    if err.errno:
                        client_logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError, TypeError):
                    client_logger.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                finally:
                    self.transport.settimeout(5)

                # Если сообщение получено, то вызываем функцию обработчик:
                if message:
                    client_logger.debug(f'Принято сообщение с сервера: {message}')
                    self.process_server_ans(message)
