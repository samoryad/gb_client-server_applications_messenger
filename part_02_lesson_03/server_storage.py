import datetime
from sqlalchemy import Column, Integer, String, create_engine, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from my_messenger.common.utils import get_configs

CONFIGS = get_configs()


# класс хранилища сервера
class ServerStorage:
    # используем декларативный подход
    BASE = declarative_base()

    # класс всех пользователей (id, имя пользователя, время последнего посещения)
    # Экземпляр этого класса = запись в таблице all_users
    class AllUsers(BASE):
        __tablename__ = 'all_users'
        id = Column(Integer, primary_key=True)
        user_name = Column(String, unique=True)
        last_login_time = Column(DateTime)

        def __init__(self, user_name):
            self.user_name = user_name
            self.last_login_time = datetime.datetime.now()

    # класс активных пользователей (id, имя пользователя, ip-адрес, port, время входа)
    class ActiveUsers(BASE):
        __tablename__ = 'active_users'
        id = Column(Integer, primary_key=True)
        user_name = Column(String, ForeignKey('all_users.id'), unique=True)
        ip_address = Column(String)
        port = Column(Integer)
        login_time = Column(DateTime)

        def __init__(self, user_name, ip_address, port, login_time):
            self.user_name = user_name
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    # класс истории о посещавших пользователях (id, имя пользователя, ip-адрес, порт, время последнего посещения)
    class LoginHistory(BASE):
        __tablename__ = 'login_history'
        id = Column(Integer, primary_key=True)
        user_name = Column(String, ForeignKey('all_users.id'), unique=True)
        ip_address = Column(String)
        port = Column(Integer)
        last_login_time = Column(DateTime)

        def __init__(self, user_name, ip_address, port, last_login_time):
            self.user_name = user_name
            self.ip_address = ip_address
            self.port = port
            self.last_login_time = last_login_time

    def __init__(self):
        # создаём движок базы данных (без логирования и с переподключением каждые 2 часа)
        self.ENGINE = create_engine(CONFIGS.get('SERVER_DATABASE_PATH'), echo=False, pool_recycle=7200)

        # через объект метаданных создаём описанные таблицы
        self.BASE.metadata.create_all(self.ENGINE)
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
        # print(type(users_query))
        # print(users_query)

        # если пользователь есть, то просто обновляем ему время посещения
        if users_query.count():
            user = users_query.first()
            # print(user)
            user.login_time = datetime.datetime.now()
        # если нет, то вносим его данные в сессию
        else:
            user = self.AllUsers(login_user)
            # print(user)
            self.session.add(user)
            # print(self.session)
            self.session.commit()

        # создаём экземпляр класса активных пользователей и через него вносим в таблицу активных
        # пользователей данные (имя пользователя, ip-адрес, порт и время)
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        # print(new_active_user)
        self.session.add(new_active_user)

        # тоже самое делаем и с историей входа: создаём экземпляр класса истории и через него
        # вносим в таблицу данные о пользователе (имя пользователя, ip-адрес, порт и время)
        history = self.LoginHistory(user.id, ip_address, port, datetime.datetime.now())
        # print(history)
        self.session.add(history)

        # подтверждаем изменения
        self.session.commit()

    def logout_user(self, user_name):
        # получаем из таблицы all_users пользователя, который захотел выйти
        exit_user = self.session.query(self.AllUsers).filter_by(user_name=user_name).first()

        # и удаляем его из таблицы активных пользователей по id
        self.session.query(self.ActiveUsers).filter_by(user_name=exit_user.id).delete()

        # подтверждаем изменения
        self.session.commit()

    # метод получения списка всех пользователей
    def all_users_list(self):
        # делаем запрос из таблицы all_users (id, user_name, last_login_time)
        query = self.session.query(
            self.AllUsers.id,
            self.AllUsers.user_name,
            self.AllUsers.last_login_time
        )
        # возвращаем список кортежей для вывода
        return query.all()

    # метод получения списка активных пользователей
    def active_users_list(self):
        # делаем запрос на соединение таблиц all_users (id, user_name) и active_users (ip_address, port, login_time)
        query = self.session.query(
            self.AllUsers.id,
            self.AllUsers.user_name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # возвращаем список кортежей для вывода
        return query.all()

    # метод получения истории чата
    def show_history(self):
        # соединяем запросы из таблицы all_users (id, user_name) и login_history(ip_address, port, last_login_time)
        query = self.session.query(
            self.AllUsers.id,
            self.AllUsers.user_name,
            self.LoginHistory.ip_address,
            self.LoginHistory.port,
            self.LoginHistory.last_login_time
        ).join(self.AllUsers)
        # возвращаем список кортежей для вывода
        return query.all()


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
    print(database.show_history())
    # логинимся ещё одним
    database.login_user('Shakhen', '192.168.1.2', 6666)
    # показываем историю
    print(database.show_history())
    # выводим активных пользователей
    print(database.active_users_list())
