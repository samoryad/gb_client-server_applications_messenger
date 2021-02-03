# 1.	Задание на закрепление знаний по модулю CSV. Написать скрипт,
# осуществляющий выборку определенных данных из файлов info_1.txt, info_2.txt, info_3.txt и
# формирующий новый «отчетный» файл в формате CSV. Для этого:
# a. Создать функцию get_data(), в которой в цикле осуществляется перебор файлов с данными,
# их открытие и считывание данных. В этой функции из считанных данных необходимо с помощью
# регулярных выражений извлечь значения параметров «Изготовитель системы»,  «Название ОС»,
# «Код продукта», «Тип системы». Значения каждого параметра поместить в соответствующий список.
# Должно получиться четыре списка — например, os_prod_list, os_name_list, os_code_list, os_type_list.
# В этой же функции создать главный список для хранения данных отчета — например, main_data —
# и поместить в него названия столбцов отчета в виде списка: «Изготовитель системы», «Название ОС»,
# «Код продукта», «Тип системы». Значения для этих столбцов также оформить в виде списка и поместить
# в файл main_data (также для каждого файла);
import csv
import re


def get_data():
    os_prod_list = []
    os_name_list = []
    os_code_list = []
    os_type_list = []
    main_data = ['Изготовитель системы', 'Название ОС', 'Код продукта', 'Тип системы']
    for i in range(1, 4):
        with open(f'info_{i}.txt', encoding='windows-1251') as file:
            list_os = csv.reader(file, delimiter=':')
            for row in list_os:
                if main_data[0] in row:
                    row_no_spaces = re.sub(r'^\s+', '', row[1])
                    os_prod_list.append(row_no_spaces)
                if main_data[1] in row:
                    row_no_spaces = re.sub(r'^\s+', '', row[1])
                    os_name_list.append(row_no_spaces)
                if main_data[2] in row:
                    row_no_spaces = re.sub(r'^\s+', '', row[1])
                    os_code_list.append(row_no_spaces)
                if main_data[3] in row:
                    row_no_spaces = re.sub(r'^\s+', '', row[1])
                    os_type_list.append(row_no_spaces)

    main_data.append(os_prod_list)
    main_data.append(os_name_list)
    main_data.append(os_code_list)
    main_data.append(os_type_list)
    print(os_prod_list)
    print(os_name_list)
    print(os_code_list)
    print(os_type_list)
    print(main_data)


get_data()
