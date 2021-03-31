from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import datetime

from my_messenger.common.utils import get_configs

CONFIGS = get_configs()


# Класс - серверная база данных:
class ServerStorage:
    # Класс - отображение таблицы всех пользователей
    class AllUsers:
        def __init__(self, username):
            self.id = None
            self.user_name = username
            self.last_login_time = datetime.datetime.now()

    # класс активных пользователей (id, имя пользователя, ip-адрес, port, время входа)
    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user_name = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    # класс истории о посещавших пользователях (id, имя пользователя, ip-адрес, порт, время последнего посещения)
    class LoginHistory:
        def __init__(self, name, ip, port, date):
            self.id = None
            self.user_name = name
            self.ip_address = ip
            self.port = port
            self.last_login_time = date

    # класс отображения таблицы контактов пользователей (id, имя пользователя, контакт)
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user_name = user
            self.contact = contact

    # класс отображения таблицы истории действий (id, имя пользователя, кол-во отправленных и полученных сообшений)
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user_name = user
            self.sent_messages = 0
            self.accepted_messages = 0

    def __init__(self, path):
        # создаём движок базы данных (без логирования и с переподключением каждые 2 часа)
        self.ENGINE = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу пользователей
        all_users_table = Table('all_users', self.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('user_name', String, unique=True),
                                Column('last_login_time', DateTime)
                                )

        # Создаём таблицу активных пользователей
        active_users_table = Table('active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user_name', ForeignKey('all_users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Создаём таблицу истории входов
        user_login_history_table = Table('login_history', self.metadata,
                                         Column('id', Integer, primary_key=True),
                                         Column('user_name', ForeignKey('all_users.id')),
                                         Column('ip_address', String),
                                         Column('port', String),
                                         Column('last_login_time', DateTime),
                                         )

        # Создаём таблицу контактов пользователей
        users_contacts = Table('contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('user_name', ForeignKey('all_users.id')),
                               Column('contact', ForeignKey('all_users.id'))
                               )

        # Создаём таблицу истории пользователей
        users_history_table = Table('users_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user_name', ForeignKey('all_users.id')),
                                    Column('sent_messages', Integer),
                                    Column('accepted_messages', Integer)
                                    )

        # создаём таблицы
        self.metadata.create_all(self.ENGINE)

        # создаём отображения (мостики)
        mapper(self.AllUsers, all_users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history_table)
        mapper(self.UsersContacts, users_contacts)
        mapper(self.UsersHistory, users_history_table)

        # создаём объект сессии
        SESSION = sessionmaker(bind=self.ENGINE)
        self.session = SESSION()

        # обнуляем таблицу активных пользователей при новом соединении (если они остались)
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # метод, фиксирующий вход пользователя и внесение его в базу
    def login_user(self, login_user, ip_address, port):
        # делаем запрос в таблицу всех пользователей на наличие пользователя с конкретным именем
        users_query = self.session.query(self.AllUsers).filter_by(user_name=login_user)

        # если пользователь есть, то просто обновляем ему время посещения
        if users_query.count():
            user = users_query.first()
            user.last_login_time = datetime.datetime.now()
        # Если нету, то создаздаём нового пользователя
        else:
            user = self.AllUsers(login_user)
            self.session.add(user)
            # Комит здесь нужен, чтобы присвоился ID
            self.session.commit()
            # вносим в историю
            user_in_history = self.UsersHistory(user.id)
            self.session.add(user_in_history)

        # создаём экземпляр класса активных пользователей и через него вносим в таблицу активных
        # пользователей данные (имя пользователя, ip-адрес, порт и время)
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # тоже самое делаем и с историей входа: создаём экземпляр класса истории и через него
        # вносим в таблицу данные о пользователе (имя пользователя, ip-адрес, порт и время)
        history = self.LoginHistory(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(history)

        # подтверждаем изменения
        self.session.commit()

    # метод, фиксирующий отключение пользователя
    def logout_user(self, user_name):
        # получаем из таблицы all_users пользователя, который захотел выйти
        exit_user = self.session.query(self.AllUsers).filter_by(user_name=user_name).first()

        # и удаляем его из таблицы активных пользователей по id
        self.session.query(self.ActiveUsers).filter_by(user_name=exit_user.id).delete()

        # подтверждаем изменения
        self.session.commit()

    # метод фиксирует передачу сообщения и делает соответствующие отметки в БД
    def process_message(self, sender, recipient):
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(user_name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(user_name=recipient).first().id

        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersHistory).filter_by(user_name=sender).first()
        sender_row.sent_messages += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user_name=recipient).first()
        recipient_row.accepted_messages += 1

        # подтверждаем изменения
        self.session.commit()

    # метод добавления контакта пользователя
    def add_contact(self, user, contact):
        # получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(user_name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(user_name=contact).first()

        # проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем)
        if not contact or self.session.query(self.UsersContacts).filter_by(user_name=user.id,
                                                                           contact=contact.id).count():
            return

        # создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)

        self.session.commit()

    # метод удаляет контакт из базы данных
    def remove_contact(self, user, contact):
        # получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(user_name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(user_name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return

        # удаляем требуемое
        self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user_name == user.id,
            self.UsersContacts.contact == contact.id
        ).delete()
        self.session.commit()

    # метод получения списка всех пользователей
    def all_users_list(self):
        # делаем запрос из таблицы all_users (id, user_name, last_login_time)
        query = self.session.query(
            self.AllUsers.user_name,
            self.AllUsers.last_login_time
        )
        # Возвращаем список кортежей
        return query.all()

    # метод получения списка активных пользователей
    def active_users_list(self):
        # делаем запрос на соединение таблиц all_users (id, user_name) и active_users (ip_address, port, login_time)
        query = self.session.query(
            self.AllUsers.user_name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # метод получения истории чата (по пользователю или всем пользователям)
    def login_history(self, username=None):
        # соединяем запросы из таблицы all_users (user_name) и login_history(ip_address, port, last_login_time)
        query = self.session.query(self.AllUsers.user_name,
                                   self.LoginHistory.ip_address,
                                   self.LoginHistory.port,
                                   self.LoginHistory.last_login_time
                                   ).join(self.AllUsers)
        # если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.user_name == username)
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список контактов пользователя.
    def get_contacts(self, username):
        # Запрашивааем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(user_name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.user_name). \
            filter_by(user_name=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # метод возвращает количество переданных и полученных сообщений
    def message_history(self):
        # соединяем запросы из таблицы all_users (user_name, last_login_time) и
        # users_history(sent_messages, accepted_messages)
        query = self.session.query(
            self.AllUsers.user_name,
            self.AllUsers.last_login_time,
            self.UsersHistory.sent_messages,
            self.UsersHistory.accepted_messages
        ).join(self.AllUsers)
        # возвращаем список кортежей
        return query.all()


# Отладка
if __name__ == '__main__':
    # создаём экзампляр класса хранилища
    database = ServerStorage()
    # логинимся
    database.login_user('Samoryad', '192.168.1.0', 8888)
    database.login_user('Ashot', '192.168.1.3', 9999)
    database.login_user('Gogi', '192.168.1.1', 7777)
    # выводим всех пользователей
    print(database.all_users_list())
    # выводим активных пользователей
    print(database.active_users_list())
    # разлогиниваем одного из них
    database.logout_user('Ashot')
    # выводим всех пользователей
    print(database.all_users_list())
    # выводим активных пользователей
    print(database.active_users_list())
    # показываем историю
    print(database.login_history())
    print(database.login_history('Ashot'))
    # логинимся ещё одним
    database.login_user('Shakhen', '192.168.1.2', 6666)
    # показываем историю
    print(database.login_history())
    # выводим активных пользователей
    print(database.active_users_list())
    # посылаем сообщение
    database.process_message('Samoryad', 'Gogi')
    print(database.message_history())
    # добавляем контакты
    database.add_contact('Samoryad', 'contact1')
    database.add_contact('Gogi', 'contact2')
    database.remove_contact('Samoryad', 'contact1')
    print(database.get_contacts('Samoryad'))
    print(database.get_contacts('Gogi'))
