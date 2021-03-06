# 6. Создать текстовый файл test_file.txt, заполнить его тремя строками:
# «сетевое программирование», «сокет», «декоратор». Проверить кодировку файла по умолчанию.
# Принудительно открыть файл в формате Unicode и вывести его содержимое.
test_file = open('test-file.txt', 'w', encoding='utf-8')
test_file.write('сетевое программирование \nсокет \nдекоратор')
test_file.close()
# в принте будет видно кодировку (понятно, что это будет 'utf-8', при создании других типов вылезают ошибки)
print(test_file)

with open('test-file.txt', 'r', encoding='utf-8') as file:
    for line in file:
        print(line)

# пробовал создавать файлы в других кодировках в notepad++ (ANSI, Windows-1251), но почему-то при
# открытии они автоматически переделываются на utf-8
# У меня по умолчанию cp1252 (locale.getpreferredencoding())
