# 4. Преобразовать слова «разработка», «администрирование», «protocol»,
# «standard» из строкового представления в байтовое и выполнить обратное
# преобразование (используя методы encode и decode).
str_01 = 'разработка'
enc_str_bytes_01 = str_01.encode('utf-8')
print(enc_str_bytes_01)
dec_str_01 = enc_str_bytes_01.decode('utf-8')
print(dec_str_01)

str_02 = 'администрирование'
enc_str_bytes_02 = str_02.encode('utf-8')
print(enc_str_bytes_02)
dec_str_02 = enc_str_bytes_02.decode('utf-8')
print(dec_str_02)

str_03 = 'protocol'
enc_str_bytes_03 = str_03.encode('utf-8')
print(enc_str_bytes_03)
dec_str_03 = enc_str_bytes_03.decode('utf-8')
print(dec_str_03)

str_04 = 'standard'
enc_str_bytes_04 = str_04.encode('utf-8')
print(enc_str_bytes_04)
dec_str_04 = enc_str_bytes_04.decode('utf-8')
print(dec_str_04)
