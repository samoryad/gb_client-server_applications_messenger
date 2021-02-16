import logging
from logging.handlers import TimedRotatingFileHandler

# Сообщения лога должны иметь следующий формат: "<дата-время> <уровень_важности> <имя_модуля> <сообщение>"
_log_format = f'%(asctime)s - %(levelname)s - %(module)s - %(message)s '
# Создаем объект форматирования
formatter = logging.Formatter(_log_format)

# Создаем файловый обработчик логирования (можно задать кодировку)
# Журналирование должно производиться в лог-файл
file_handler = logging.FileHandler("log/server/server.main.log", encoding='utf-8')
file_handler.setFormatter(formatter)

# На стороне сервера необходимо настроить ежедневную ротацию лог-файлов.
time_rotating_handler = TimedRotatingFileHandler("log/server/server.main.log", when='d', interval=1,
                                                 backupCount=7, encoding='utf-8')
# file_handler.setLevel(logging.DEBUG)
time_rotating_handler.setFormatter(formatter)

# Создание именованного логгера
server_logger = logging.getLogger('server.main')

# Добавляем в логгер новый обработчик событий и устанавливаем уровень логирования
# server_logger.addHandler(file_handler)
server_logger.addHandler(time_rotating_handler)
server_logger.setLevel(logging.DEBUG)

'''
# проверяем
server_logger.info('Тестовый запуск логирования')
server_logger.warning('Тестовый запуск логирования')

# меняем уровень логирования
server_logger.setLevel(logging.WARNING)

# проверяем
server_logger.debug('Тестовый запуск логирования')
server_logger.critical('Тестовый запуск логирования')
'''
