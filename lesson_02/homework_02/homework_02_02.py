# 2. Задание на закрепление знаний по модулю json. Есть файл orders в формате JSON
# с информацией о заказах. Написать скрипт, автоматизирующий его заполнение данными. Для этого:
# a. Создать функцию write_order_to_json(), в которую передается 5 параметров — товар (item),
# количество (quantity), цена (price), покупатель (buyer), дата (date). Функция должна
# предусматривать запись данных в виде словаря в файл orders.json. При записи данных
# указать величину отступа в 4 пробельных символа
import json


def write_order_to_json(item, quantity, price, buyer, date):
    dict_to_json = {"orders": [item, quantity, price, buyer, date]}
    with open('orders.json', 'w', encoding='utf-8') as json_file:
        json.dump(dict_to_json, json_file, indent=4)


# b.Проверить работу программы через вызов функции write_order_to_json() с передачей в нее
# значений каждого параметра.
write_order_to_json('Notebook Dell', 3, 75000, 'geekbrains', '03.02.2021')
