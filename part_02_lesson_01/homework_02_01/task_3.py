"""
Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате
(использовать модуль tabulate). Таблица должна состоять из двух колонок
"""
from tabulate import tabulate
from part_02_lesson_01.homework_02_01.task_2 import host_range_ping


# функция вывода результата работы проверки доступности ip-адресов host_range_ping() в табличном виде
def host_range_ping_tab():
    dict_to_tab = host_range_ping()
    print(tabulate([dict_to_tab], headers='keys', tablefmt="grid", stralign="center"))


if __name__ == '__main__':
    host_range_ping_tab()
