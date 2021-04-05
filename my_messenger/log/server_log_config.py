import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

sys.path.append('../')

# Сообщения лога должны иметь следующий формат: "<дата-время>
# <уровень_важности> <имя_модуля> <сообщение>"
_log_format = f'%(asctime)s - %(levelname)s - %(module)s - %(message)s '
# Создаем объект форматирования
server_formatter = logging.Formatter(_log_format)

# Подготовка имени файла для логирования
path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(path, 'server.log')

# создаём потоки вывода логов
steam = logging.StreamHandler(sys.stderr)
steam.setFormatter(server_formatter)
steam.setLevel(logging.INFO)
# На стороне сервера необходимо настроить ежедневную ротацию лог-файлов.
log_file = logging.handlers.TimedRotatingFileHandler(
    path, encoding='utf8', interval=1, when='D')
log_file.setFormatter(server_formatter)

# Создание именованного логгера
server_logger = logging.getLogger('server')

# Добавляем в логгер новый обработчик событий и устанавливаем уровень
# логирования
server_logger.addHandler(steam)
server_logger.addHandler(log_file)
server_logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    # проверяем
    server_logger.info('Тестовый запуск логирования')
    server_logger.warning('Тестовый запуск логирования')

    # меняем уровень логирования
    server_logger.setLevel(logging.WARNING)

    # проверяем
    server_logger.debug('Тестовый запуск логирования')
    server_logger.critical('Тестовый запуск логирования')
