import dis


# Метакласс для проверки соответствия сервера:
class ServerVerifier(type):
    def __init__(cls, cls_name, bases, cls_dict):
        # cls_name - экземпляр метакласса - Server
        # bases - кортеж базовых классов - ()
        # cls_dict - словарь атрибутов и методов экземпляра метакласса

        # print(cls_dict)
        # мой cls_dict:
        # {'__module__': '__main__',
        # '__qualname__': 'Server',
        # '__init__': <function Server.__init__ at 0x0000021FFF2AA0D0>,
        # 'arg_parser': <function Server.arg_parser at 0x0000021FFF2AA280>,
        # 'check_presence_message': <function Server.check_presence_message at 0x0000021FFF2AA3A0>,
        # 'check_message_from_chat': <function Server.check_message_from_chat at 0x0000021FFF2AA4C0>,
        # 'init_socket': <function Server.init_socket at 0x0000021FFF2AA160>,
        # 'main': <function Server.main at 0x0000021FFF2AA550>}

        # Список методов, которые используются в функциях класса:
        methods_list = []
        # Атрибуты, используемые в функциях классов
        attrs_list = []

        # перебираем ключи
        for func in cls_dict:
            # Пробуем
            try:
                # Возвращает итератор по инструкциям в предоставленной функции
                # , методе, строке исходного кода или объекте кода.
                return_iter = dis.get_instructions(cls_dict[func])
                # пример вывода итератора
                # ret - <generator object _get_instructions_bytes at 0x00000062EAEAD7C8>
                # Если не функция то ловим исключение
            except TypeError:
                pass
            else:
                # Раз функция разбираем код, получая используемые методы и атрибуты.
                for instruction in return_iter:
                    # print(instruction)

                    # пример одной инструкции:
                    # Instruction(opname='LOAD_GLOBAL', opcode=116, arg=0, argval='argparse',
                    # argrepr='argparse', offset=0, starts_line=19, is_jump_target=False)
                    # opname - имя для операции
                    if instruction.opname == 'LOAD_GLOBAL':
                        if instruction.argval not in methods_list:
                            # заполняем список методами, использующимися в функциях класса
                            methods_list.append(instruction.argval)
                    elif instruction.opname == 'LOAD_ATTR':
                        if instruction.argval not in attrs_list:
                            # заполняем список атрибутами, использующимися в функциях класса
                            attrs_list.append(instruction.argval)
        print(f'список методов класса {cls_name} (информация от метакласса) {methods_list}')
        print(f'список атрибутов класса {cls_name} (информация от метакласса) {attrs_list}')
        # Если обнаружено использование недопустимого метода connect, бросаем исключение:
        if 'connect' in methods_list:
            raise TypeError('Использование метода connect недопустимо в серверном классе')
        # Если сокет не инициализировался константами SOCK_STREAM(TCP) AF_INET(IPv4), тоже исключение.
        if not ('SOCK_STREAM' in attrs_list and 'AF_INET' in attrs_list):
            raise TypeError('Некорректная инициализация сокета. Нужна инициализация по TCP')
        # Обязательно вызываем конструктор предка:
        super().__init__(cls_name, bases, cls_dict)


class ClientVerifier(type):
    def __init__(cls, cls_name, bases, cls_dict):
        # список для методов класса
        methods_list = []
        for func in cls_dict:
            try:
                return_iter = dis.get_instructions(cls_dict[func])
            except TypeError:
                pass
            else:
                for instruction in return_iter:
                    # print(instruction)
                    if instruction.opname == 'LOAD_GLOBAL':
                        if instruction.argval not in methods_list:
                            # заполняем список методами, использующимися в функциях класса
                            methods_list.append(instruction.argval)

        print(f'список методов класса {cls_name} (информация от метакласса) {methods_list}')
        for method in methods_list:
            if method == 'accept' or method == 'listen':
                raise TypeError('Использование метода accept, listen недопустимо в клиенте')

        super().__init__(cls_name, bases, cls_dict)
