# 3. Определить, какие из слов «attribute», «класс», «функция», «type»
# невозможно записать в байтовом типе.
byte_attribute = b'attribute'
print(type(byte_attribute))
print(byte_attribute)

# byte_class = b'класс'
# print(type(byte_class))
# print(byte_class)

# byte_function = b'функция'
# print(type(byte_function))
# print(byte_function)

byte_type = b'type'
print(type(byte_type))
print(byte_type)

# невозможно записать слова "класс" и "функция", потому что в кодировке ASCII
# не предусмотрено преобразование кириллицы в байты