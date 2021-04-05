Common package
==============

Пакет общих утилит, использующихся в разных модулях проекта.

Скрипт answers.py
-----------------

Содержит словари - ответы сервера

Скрипт configs.json
-------------------

json файл с константами проекта

Скрипт decorators.py
--------------------

Декораторы логирования:

common.decorators. **log** (func_to_log)

Декоратор, выполняющий логирование вызовов функций.
Сохраняет события типа debug, содержащие информацию о имени вызываемой
функиции, параметры с которыми вызывается функция, и модуль, вызывающий функцию.

и common.decorators. **Log** ()

Декоратор, выполняющий логирование вызовов функций.
Сохраняет события типа info, содержащие информацию о имени вызываемой
функиции, параметры с которыми вызывается функция, и модуль, вызывающий функцию.

common.decorators. **login_required** (func)

Декоратор, проверяющий, что клиент авторизован на сервере. Проверяет, что
передаваемый объект сокета находится в списке авторизованных клиентов.
За исключением передачи словаря-запроса на авторизацию. Если клиент не
авторизован, генерирует исключение TypeError

.. automodule:: common.decorators
    :members:

Скрипт descryptors.py
---------------------

.. autoclass:: common.descryptors.Port
    :members:

Скрипт errors.py
----------------

.. autoclass:: common.errors.IncorrectDataReceivedError
    :members:

.. autoclass:: common.errors.ServerError
    :members:

.. autoclass:: common.errors.NonDictInputError
    :members:

.. autoclass:: common.errors.ReqFieldMissingError
    :members:

Скрипт metaclasses.py
-----------------------

.. autoclass:: common.metaclasses.ServerMaker
    :members:

.. autoclass:: common.metaclasses.ClientMaker
    :members:

Скрипт utils.py
---------------------

common.utils. **get_message** (opened_socket, CONFIGS)

Функция приёма сообщений от удалённых компьютеров. Принимает сообщения JSON,
декодирует полученное сообщение и проверяет что получен словарь.

common.utils. **send_message** (opened_socket, message, CONFIGS)

Функция отправки словарей через сокет. Кодирует словарь в формат JSON и
отправляет через сокет.

common.utils. **get_configs** ()

Функция получения словаря из json файла с настройками
