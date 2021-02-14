import json


# функция перевода сообщения из байтов с помощью json
def get_data_from_message(response):
    return json.loads(response.decode('utf-8'))


# функция перевода сообщения в байты с помощью json
def send_message(socket, data_dict):
    socket.send(json.dumps(data_dict).encode('utf-8'))


# функция получения словаря из json файла с настройками
def get_settings():
    with open('common/settings.json') as f_n:
        objs = json.load(f_n)
        return objs
