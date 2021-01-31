# 1. Каждое из слов «разработка», «сокет», «декоратор» представить в строковом формате и
# проверить тип и содержание соответствующих переменных. Затем с помощью онлайн-конвертера
# преобразовать строковые представление в формат Unicode и также проверить тип и содержимое переменных.
word_1 = 'разработка'
print(type(word_1))
print(word_1)

word_2 = 'сокет'
print(type(word_2))
print(word_2)

word_3 = 'декоратор'
print(type(word_3))
print(word_3)

word_1_unic = '\u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0430'
print(type(word_1_unic))
print(word_1_unic)

word_2_unic = '\u0441\u043e\u043a\u0435\u0442'
print(type(word_2_unic))
print(word_2_unic)

word_3_unic = '\u0434\u0435\u043a\u043e\u0440\u0430\u0442\u043e\u0440'
print(type(word_3_unic))
print(word_3_unic)
