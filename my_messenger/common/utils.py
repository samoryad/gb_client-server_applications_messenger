import json
import os
import sys
from my_messenger.common.errors import IncorrectDataReceivedError


def get_message(opened_socket, CONFIGS):
    """
    Функция приёма сообщений от удалённых компьютеров.
    Принимает сообщения JSON, декодирует полученное сообщение
    и проверяет что получен словарь.
    :param opened_socket: сокет для передачи данных.
    :param CONFIGS: конфигурация.
    :return: словарь - сообщение.
    """
    encoded_response = opened_socket.recv(CONFIGS.get('MAX_PACKAGE_LENGTH'))
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(CONFIGS.get('ENCODING'))
        response_dict = json.loads(json_response)
        if isinstance(response_dict, dict):
            return response_dict
        raise IncorrectDataReceivedError
    raise IncorrectDataReceivedError


def send_message(opened_socket, message, CONFIGS):
    """
    Функция отправки словарей через сокет.
    Кодирует словарь в формат JSON и отправляет через сокет.
    :param opened_socket: сокет для передачи
    :param message: словарь для передачи
    :param CONFIGS: конфигурация.
    :return: ничего не возвращает
    """
    json_message = json.dumps(message)
    encoded_message = json_message.encode(CONFIGS.get('ENCODING'))
    opened_socket.send(encoded_message)


def get_configs():
    """
    функция получения словаря из json файла с настройками
    """
    if not os.path.exists('common/configs.json'):
        print('Файл конфигурации не найден')
        sys.exit(1)
    with open('common/configs.json') as configs_file:
        CONFIGS = json.load(configs_file)
        return CONFIGS
