import sys
import traceback
from functools import wraps
import logging

if sys.argv[0].find('client') == -1:
    LOGGER = logging.getLogger('server.main')
else:
    LOGGER = logging.getLogger('client.main')


def log():
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            LOGGER.info(
                f'Функция {func.__name__} вызвана из функции {traceback.format_stack()[0].strip().split()[-1]}.'
            )
            res = func(*args, **kwargs)
            return res

        return decorated

    return decorator


class Log():
    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):
            LOGGER.info(
                f'Функция {func.__name__} вызвана из функции {traceback.format_stack()[0].strip().split()[-1]}.'
            )
            # Декорированная функция
            res = func(*args, **kwargs)
            return res

        return decorated
