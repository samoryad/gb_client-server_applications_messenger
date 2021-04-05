import socket
import sys
import traceback
from functools import wraps
import logging

from my_messenger.common.utils import get_configs

sys.path.append('../')

if sys.argv[0].find('client') == -1:
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('client')

CONFIGS = get_configs()


def log(func_to_log):
    """
    Декоратор, выполняющий логирование вызовов функций.
    Сохраняет события типа debug, содержащие
    информацию о имени вызываемой функиции, параметры с которыми
    вызывается функция, и модуль, вызывающий функцию.
    """
    def log_saver(*args, **kwargs):
        LOGGER.debug(
            f'Была вызвана функция {func_to_log.__name__} '
            f'c параметрами {args} , {kwargs}. '
            f'Вызов из модуля {func_to_log.__module__}')
        ret = func_to_log(*args, **kwargs)
        return ret

    return log_saver


class Log():
    """
    Декоратор, выполняющий логирование вызовов функций.
    Сохраняет события типа info, содержащие
    информацию о имени вызываемой функиции, параметры с которыми
    вызывается функция, и модуль, вызывающий функцию.
    """
    def __call__(self, func):
        @wraps(func)
        def decorated(*args, **kwargs):
            LOGGER.info(
                f'Функция {func.__name__} вызвана из функции '
                f'{traceback.format_stack()[0].strip().split()[-1]}.'
            )
            # Декорированная функция
            res = func(*args, **kwargs)
            return res

        return decorated


def login_required(func):
    """
    Декоратор, проверяющий, что клиент авторизован на сервере.
    Проверяет, что передаваемый объект сокета находится в
    списке авторизованных клиентов.
    За исключением передачи словаря-запроса
    на авторизацию. Если клиент не авторизован,
    генерирует исключение TypeError
    """

    def checker(*args, **kwargs):
        # проверяем, что первый аргумент - экземпляр MessageProcessor
        # Импортить необходимо тут, иначе ошибка рекурсивного импорта.
        from my_messenger.server.core import MessageProcessor
        if isinstance(args[0], MessageProcessor):
            found = False
            for arg in args:
                if isinstance(arg, socket.socket):
                    # Проверяем, что данный сокет есть в списке names класса
                    # MessageProcessor
                    for client in args[0].names:
                        if args[0].names[client] == arg:
                            found = True

            # Теперь надо проверить, что передаваемые аргументы не presence
            # сообщение. Если presence, то разрешаем
            for arg in args:
                if isinstance(arg, dict):
                    if CONFIGS['ACTION'] in arg and \
                            arg[CONFIGS['ACTION']] == CONFIGS['PRESENCE']:
                        found = True
            # Если не не авторизован и не сообщение начала авторизации, то
            # вызываем исключение.
            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker
