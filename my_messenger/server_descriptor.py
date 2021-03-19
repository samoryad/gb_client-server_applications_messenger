from my_messenger.log.server_log_config import server_logger


class CheckPort:
    """дескриптор данных"""

    # проверяет корректность выбора порта
    def __set__(self, instance, value):
        # instance - <__main__.Server object at 0x0000016926F4A820>
        if not 65535 >= value >= 1024:
            server_logger.critical("Дескриптор - Порт должен быть указан в пределах от 1024 до 65535")
            print("Дескриптор - Порт должен быть указан в пределах от 1024 до 65535")
            exit(1)
        instance.__dict__[self.my_attr] = value

    def __set_name__(self, owner, my_attr):
        # owner - владелец атрибута - <class '__main__.Server'>
        # my_attr - имя атрибута владельца - listen_port
        self.my_attr = my_attr
