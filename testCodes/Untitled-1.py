def a():
    a = input("입력")
    while a in num_list:
        a = input("다시입력")


num_list = []


for i in range(6):
    a()
