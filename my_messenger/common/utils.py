import json
import os
import sys
from my_messenger.errors import IncorrectDataReceivedError, NonDictInputError

# функция получения и перевода сообщения из байтов с помощью json
def get_message(opened_socket, CONFIGS):
    encoded_response = opened_socket.recv(CONFIGS.get('MAX_PACKAGE_LENGTH'))
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(CONFIGS.get('ENCODING'))
        response_dict = json.loads(json_response)
        if isinstance(response_dict, dict):
            return response_dict
        raise IncorrectDataReceivedError
    raise IncorrectDataReceivedError


# функция перевода сообщения в байты с помощью json и отправки
def send_message(opened_socket, message, CONFIGS):
    json_message = json.dumps(message)
    encoded_message = json_message.encode(CONFIGS.get('ENCODING'))
    opened_socket.send(encoded_message)


# функция получения словаря из json файла с настройками
def get_configs():
    if not os.path.exists('common/configs.json'):
        print('Файл конфигурации не найден')
        sys.exit(1)
    with open('common/configs.json') as configs_file:
        CONFIGS = json.load(configs_file)
        return CONFIGS


def read_requests(r_clients, all_clients, CONFIGS):
    # Чтение запросов из списка клиентов
    responses = {}  # Словарь ответов сервера вида {сокет: запрос}

    for sock in r_clients:
        print(sock)
        print(r_clients)
        try:
            data = sock.recv(CONFIGS.get('MAX_PACKAGE_LENGTH')).decode(CONFIGS.get('ENCODING'))
            responses[sock] = data
        except:
            print(f'Клиент {sock.fileno()} {sock.getpeername()} отключился')
            all_clients.remove(sock)

    return responses


def write_responses(requests, w_clients, all_clients, CONFIGS):
    # Эхо-ответ сервера клиентам, от которых были запросы

    for sock in w_clients:
        for _, request in requests.items():
            try:
                # Подготовить и отправить ответ сервера
                resp = request.encode(CONFIGS.get('ENCODING'))
                # Эхо-ответ сделаем чуть непохожим на оригинал
                sock.send(resp.upper())
            except:  # Сокет недоступен, клиент отключился
                print(f'Клиент {sock.fileno()} {sock.getpeername()} отключился')
                sock.close()
                all_clients.remove(sock)
