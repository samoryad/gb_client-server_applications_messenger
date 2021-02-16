from functools import wraps
import logging


class Log():

    def __init__(self):
        # self.logging_level = logging_level
        pass

    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):
            log_format = f'%(asctime)s - %(funcName)s - %(threadName)s - %(message)s'
            formatter = logging.Formatter(log_format)
            file_handler = logging.FileHandler("log/client/log_decorator.log", encoding='utf-8')
            file_handler.setFormatter(formatter)
            log_decorator_logger = logging.getLogger('log_decorator')
            log_decorator_logger.addHandler(file_handler)
            log_decorator_logger.setLevel(logging.DEBUG)
            log_decorator_logger.info('Функция {} вызвана из функции main'.format(func.__name__))
            # Декорированная функция
            res = func(*args, **kwargs)
            return res

        return decorated
