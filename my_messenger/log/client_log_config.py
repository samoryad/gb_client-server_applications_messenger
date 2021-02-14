import logging

# Создание именованного логгера
client_logger = logging.getLogger('client.main')

# Сообщения лога должны иметь следующий формат: "<дата-время> <уровень_важности> <имя_модуля> <сообщение>"
_log_format = f'%(asctime)s - %(levelname)s - %(module)s - %(message)s '
# Создаем объект форматирования
formatter = logging.Formatter(_log_format)

# Создаем файловый обработчик логирования (можно задать кодировку)
# Журналирование должно производиться в лог-файл
file_handler = logging.FileHandler("log/client/client.main.log", encoding='utf-8')
file_handler.setFormatter(formatter)

# Добавляем в логгер новый обработчик событий и устанавливаем уровень логирования
client_logger.addHandler(file_handler)
client_logger.setLevel(logging.DEBUG)

'''
# проверяем
client_logger.info('Тестовый запуск логирования')
client_logger.warning('Тестовый запуск логирования')

# меняем уровень логирования
client_logger.setLevel(logging.WARNING)

# проверяем
client_logger.debug('Тестовый запуск логирования')
client_logger.critical('Тестовый запуск логирования')
'''
