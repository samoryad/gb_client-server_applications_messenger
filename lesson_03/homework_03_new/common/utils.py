import json
import os
import sys


# функция приёма и перевода сообщения из байтов с помощью json
def get_message(opened_socket, CONFIGS):
    response = opened_socket.recv(CONFIGS.get('MAX_PACKAGE_LENGTH'))
    if isinstance(response, bytes):
        json_response = response.decode(CONFIGS.get('ENCODING'))
        response_dict = json.loads(json_response)
        if isinstance(response_dict, dict):
            return response_dict
        raise ValueError
    raise ValueError


# функция перевода сообщения в байты с помощью json и отправки
def send_message(opened_socket, message, CONFIGS):
    json_message = json.dumps(message)
    response = json_message.encode(CONFIGS.get('ENCODING'))
    opened_socket.send(response)


# функция получения словаря из json файла с настройками
def get_configs():
    if not os.path.exists('common/configs.json'):
        print('Файл конфигурации не найден')
        sys.exit(1)
    with open('common/configs.json') as configs_file:
        CONFIGS = json.load(configs_file)
        return CONFIGS
