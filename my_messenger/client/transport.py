import json
import socket
import sys
import time
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from my_messenger.common.errors import ServerError
from my_messenger.common.utils import get_configs, send_message, get_message
from my_messenger.log.client_log_config import client_logger
from my_messenger.log.log_decorator import Log

sys.path.append('../')
CONFIGS = get_configs()

# объект блокировки для работы с сокетом.
socket_lock = threading.Lock()


# Класс - Траннспорт, отвечает за взаимодействие с сервером
class ClientTransport(threading.Thread, QObject):
    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database = database
        # Имя пользователя
        self.username = username
        # Сокет для работы с сервером
        self.transport = None
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

    # Функция инициализации соединения с сервером
    def connection_init(self, port, ip):
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
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            client_logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        client_logger.debug('Установлено соединение с сервером')

        # Посылаем серверу приветственное сообщение и получаем ответ что всё нормально или ловим исключение.
        try:
            with socket_lock:
                send_message(self.transport, self.create_presence(), CONFIGS)
                self.process_server_ans(get_message(self.transport, CONFIGS))
        except (OSError, json.JSONDecodeError):
            client_logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # Раз всё хорошо, сообщение о установке соединения.
        client_logger.info('Соединение с сервером успешно установлено.')

    # Функция, генерирующая приветственное сообщение для сервера
    @Log()
    def create_presence(self):
        presence_message = {
            CONFIGS.get('ACTION'): CONFIGS.get('PRESENCE'),
            CONFIGS.get('TIME'): time.time(),
            CONFIGS.get('USER'): {
                CONFIGS.get('ACCOUNT_NAME'): self.username
            }
        }
        client_logger.debug(
            f'Сформировано {CONFIGS.get("PRESENCE")} сообщение для пользователя {self.username}')
        return presence_message

    # Функция обрабатывающяя сообщения от сервера. Ничего не возращает. Генерирует исключение при ошибке.
    def process_server_ans(self, message):
        client_logger.debug(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if CONFIGS.get('RESPONSE') in message:
            if message[CONFIGS.get('RESPONSE')] == 200:
                return
            elif message[CONFIGS.get('RESPONSE')] == 400:
                raise ServerError(f'{message[CONFIGS.get("ERROR")]}')
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
            self.database.save_message(message[CONFIGS.get('FROM_USER')], 'in', message[CONFIGS.get('MESSAGE_TEXT')])
            self.new_message.emit(message[CONFIGS.get('FROM_USER')])

    # Функция обновляющая контакт - лист с сервера
    def contacts_list_update(self):
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

    # Функция обновления таблицы известных пользователей.
    def user_list_update(self):
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

    # Функция сообщающая на сервер о добавлении нового контакта
    def add_contact(self, contact):
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

    # Функция удаления клиента на сервере
    def remove_contact(self, contact):
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

    # Функция закрытия соединения, отправляет сообщение о выходе.
    def transport_shutdown(self):
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

    # Функция отправки сообщения на сервер
    def send_message(self, to, message):
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
        client_logger.debug('Запущен процесс - приёмник собщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
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
                # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    client_logger.debug(f'Принято сообщение с сервера: {message}')
                    self.process_server_ans(message)
                finally:
                    self.transport.settimeout(5)
