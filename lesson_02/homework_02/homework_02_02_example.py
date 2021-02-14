# 2. Задание на закрепление знаний по модулю json. Есть файл orders в формате JSON
# с информацией о заказах. Написать скрипт, автоматизирующий его заполнение данными. Для этого:
# a. Создать функцию write_order_to_json(), в которую передается 5 параметров — товар (item),
# количество (quantity), цена (price), покупатель (buyer), дата (date). Функция должна
# предусматривать запись данных в виде словаря в файл orders.json. При записи данных
# указать величину отступа в 4 пробельных символа
import json


def write_order_to_json(item, quantity, price, buyer, date):
    orders_data = dict()
    with open('orders_sample.json', 'r') as json_file:
        orders_data = json.load(json_file)
    if not 'orders' in orders_data:
        orders_data['orders'] = []
    orders_data['orders'].append({
        'item': item,
        'quantity': quantity,
        'price': price,
        'buyer': buyer,
        'date': date
    })
    with open('orders_sample.json', 'w') as json_file:
        json.dump(orders_data, json_file, indent=4)


# b.Проверить работу программы через вызов функции write_order_to_json() с передачей в нее
# значений каждого параметра.
for i in range(1, 10):
    write_order_to_json(f'Product{i}', 4 * i, 100 * i, 'geekbrains', '03.02.2021')
