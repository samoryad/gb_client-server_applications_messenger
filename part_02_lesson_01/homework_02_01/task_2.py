"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
from ipaddress import ip_address
from pprint import pprint
from part_02_lesson_01.homework_02_01.task_1 import host_ping


# функция перебора ip-адресов из заданного диапазона
def host_range_ping():
    addr_list = []
    # проверяем корректность ввода ip-адреса
    while True:
        start_ip = input('Введите начальный ip-адрес, учтите последний октет не может быть более 254: ')
        try:
            checked_ip = ip_address(start_ip)
            break
        except ValueError:
            print('Вы ввели некорректный ip-адрес')

    # проверяем корректность ввода количества адресов
    while True:
        addr_quantity = input('Введите количество адресов для проверки: ')
        if not addr_quantity.isnumeric():
            print('Введите целое положительное число')
        else:
            # октет не может быть более 255
            if int(start_ip.split('.')[3]) + int(addr_quantity) > 254:
                print(f'Максимальное количество адресов не может быть более 254, сейчас осталось '
                      f'{254 - int(start_ip.split(".")[3])}')
            else:
                # формируем итоговый список с ip-адресами
                for i in range(0, int(addr_quantity)):
                    addr_list.append(checked_ip)
                    checked_ip += 1
                return host_ping(addr_list, 500, 1)


if __name__ == '__main__':
    pprint(host_range_ping())
