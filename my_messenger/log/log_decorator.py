from functools import wraps
import logging


def check_logging_level(logging_level):
    logging_levels = {
        'CRITICAL': 'critical',
        'ERROR': 'error',
        'WARNING': 'warning',
        'INFO': 'info',
        'DEBUG': 'debug',
        'NOTSET': 'notset',
    }
    if logging_level in logging_levels:
        return logging_levels[logging_level]
    raise ValueError


def get_decorator_logger():
    log_format = f'%(asctime)s - %(message)s'
    formatter = logging.Formatter(log_format)
    file_handler = logging.FileHandler("log/log_decorator.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    log_decorator_logger = logging.getLogger('log_decorator')
    log_decorator_logger.addHandler(file_handler)
    log_decorator_logger.setLevel(logging.DEBUG)
    return log_decorator_logger


def log():
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            get_decorator_logger().info('Функция {} вызвана из функции main'.format(func.__name__))
            res = func(*args, **kwargs)
            return res

        return decorated

    return decorator


class Log():

    def __init__(self, logging_level):
        self.logging_level = logging_level

    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):
            print(check_logging_level(self.logging_level))
            get_decorator_logger().info('Функция {} вызвана из функции main'.format(func.__name__))
            # Декорированная функция
            res = func(*args, **kwargs)
            return res

        return decorated
