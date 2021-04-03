import logging
import os
import sys

sys.path.append('../')

# Сообщения лога должны иметь следующий формат: "<дата-время> <уровень_важности> <имя_модуля> <сообщение>"
_log_format = f'%(asctime)s - %(levelname)s - %(module)s - %(message)s '
# Создаем объект форматирования
client_formatter = logging.Formatter(_log_format)

# Подготовка имени файла для логирования
path = os.path.dirname(os.path.abspath(__file__))
print(path)
path = os.path.join(path, 'client.log')
print(path)

# создаём потоки вывода логов
steam = logging.StreamHandler(sys.stderr)
steam.setFormatter(client_formatter)
steam.setLevel(logging.INFO)
log_file = logging.FileHandler(path, encoding='utf8')
log_file.setFormatter(client_formatter)

# создаём регистратор и настраиваем его
client_logger = logging.getLogger('client')
client_logger.addHandler(steam)
client_logger.addHandler(log_file)
client_logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    # проверяем
    client_logger.info('Тестовый запуск логирования')
    client_logger.warning('Тестовый запуск логирования')

    # меняем уровень логирования
    client_logger.setLevel(logging.WARNING)

    # проверяем
    client_logger.debug('Тестовый запуск логирования')
    client_logger.critical('Тестовый запуск логирования')
