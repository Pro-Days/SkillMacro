from genericpath import isfile
import pyautogui
import keyboard
from tkinter import *
from tkinter.ttk import *
import os
import time
import threading


global ongoing
global looping
looping = []
global delay
delay = 0.13
global startkey_stored
startkey_stored = True
global press_key
press_key = []


def store_all(preset):
    global HotbarKeys, Skill_timeData, start_key
    if "num1" in globals():
        Skill_timeData[0], Skill_timeData[1], Skill_timeData[2], Skill_timeData[3], Skill_timeData[4], Skill_timeData[5], Skill_timeData[6] = num1.get(
        ), num2.get(), num3.get(), num4.get(), num5.get(), num6.get(), reduce_skill_cooltime.get()
    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(" ".join(HotbarKeys) + "\n" +
                    f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n" + start_key)
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}")


def store_key():
    global HotbarKeys, Skill_timeData, start_key
    preset = combobox.get()
    keys.config(text="[]")
    HotbarKeys = []
    for i in range(6):
        key = keyboard.read_key()
        time.sleep(0.5)
        HotbarKeys.append(key)
        keys.config(text="[ " + ", ".join(HotbarKeys) + " ]")

    keys.config(text=", ".join(HotbarKeys))

    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(" ".join(HotbarKeys) + "\n" +
                    f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n" + start_key)
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}")


def store_startkey():
    global HotbarKeys, Skill_timeData, start_key
    preset = combobox.get()
    global startkey_stored
    startkey_stored = False
    start_key = keyboard.read_key()
    outtext.config(
        text=f"1~6번 입력칸: 스킬 6개 쿨타임 입력 (0이면 사용안함)\n7번 입력칸: 스킬쿨타임감소 스텟 입력\n키보드 입력 -> 스킬 사용 순서대로 키 천천히 입력\n시작 설정 -> 매크로 시작 키 설정\n{start_key}키 -> 매크로 on/off")

    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(" ".join(HotbarKeys) + "\n" +
                    f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n" + start_key)
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}")
    time.sleep(0.2)
    startkey_stored = True
    thread_key = threading.Thread(target=keyboard_clicked, daemon=True)
    thread_key.start()


def loop1(n):
    time.sleep(num1.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(0)


def loop2(n):
    time.sleep(num2.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(1)


def loop3(n):
    time.sleep(num3.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(2)


def loop4(n):
    time.sleep(num4.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(3)


def loop5(n):
    time.sleep(num5.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(4)


def loop6(n):
    time.sleep(num6.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(5)


def macro(n):

    global press_key
    press_key.append([])

    if looping[n] and num1.get() != 0:
        skill1 = threading.Thread(target=loop1, args=[n])
        skill1.start()
        keyboard.press(HotbarKeys[0])
        time.sleep(delay)

    if looping[n] and num2.get() != 0:
        skill2 = threading.Thread(target=loop2, args=[n])
        skill2.start()
        keyboard.press(HotbarKeys[1])
        time.sleep(delay)

    if looping[n] and num3.get() != 0:
        skill3 = threading.Thread(target=loop3, args=[n])
        skill3.start()
        keyboard.press(HotbarKeys[2])
        time.sleep(delay)

    if looping[n] and num4.get() != 0:
        skill4 = threading.Thread(target=loop4, args=[n])
        skill4.start()
        keyboard.press(HotbarKeys[3])
        time.sleep(delay)

    if looping[n] and num5.get() != 0:
        skill5 = threading.Thread(target=loop5, args=[n])
        skill5.start()
        keyboard.press(HotbarKeys[4])
        time.sleep(delay)

    if looping[n] and num6.get() != 0:
        skill6 = threading.Thread(target=loop6, args=[n])
        skill6.start()
        keyboard.press(HotbarKeys[5])
        time.sleep(delay)

    while looping[n]:
        if press_key[n]:
            press_key[n].sort()
            keyboard.press(HotbarKeys[press_key[n][0]])
            if press_key[n][0] == 0:
                t = threading.Thread(target=loop1, args=[n])
            elif press_key[n][0] == 1:
                t = threading.Thread(target=loop2, args=[n])
            elif press_key[n][0] == 2:
                t = threading.Thread(target=loop3, args=[n])
            elif press_key[n][0] == 3:
                t = threading.Thread(target=loop4, args=[n])
            elif press_key[n][0] == 4:
                t = threading.Thread(target=loop5, args=[n])
            elif press_key[n][0] == 5:
                t = threading.Thread(target=loop6, args=[n])
            t.start()
            del press_key[n][0]
        else:
            pass
        time.sleep(delay)


# def keyboard_is_pressed():
#     global looping
#     looping = True
#     while looping:
#         if keyboard.is_pressed("f9"):
#             looping = False
#         time.sleep(0.05)


def run_dataload(event):
    data_load()


def data_load():
    global HotbarKeys, Skill_timeData, start_key
    if "combobox" in globals():
        preset = combobox.get()
    else:
        preset = "1"
    if os.path.isfile(f"C:\ProDays\PD_SkillMacro{preset}.txt"):
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "r") as f:
            text = f.readlines()
            if preset == "1":
                if len(text) == 3:
                    SkillData = text[0].replace("\n", "")
                    HotbarKeys = SkillData.replace("\n", "").split(" ")
                    if len(HotbarKeys) != 6:
                        HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                    Skill_timeData = text[1].replace("\n", "")
                    Skill_timeData = Skill_timeData.split(" ")

                    if len(Skill_timeData) != 7:
                        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                    start_key = text[2]

                    if "num1" in globals():
                        num1.set(Skill_timeData[0])
                        num2.set(Skill_timeData[1])
                        num3.set(Skill_timeData[2])
                        num4.set(Skill_timeData[3])
                        num5.set(Skill_timeData[4])
                        num6.set(Skill_timeData[5])
                        reduce_skill_cooltime.set(Skill_timeData[6])
                else:
                    HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                    Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                    start_key = "f9"
                    store_all(preset)
            else:
                if len(text) == 1:
                    Skill_timeData = text[0].replace("\n", "")
                    Skill_timeData = Skill_timeData.split(" ")

                    if len(Skill_timeData) != 7:
                        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]

                    if "num1" in globals():
                        num1.set(Skill_timeData[0])
                        num2.set(Skill_timeData[1])
                        num3.set(Skill_timeData[2])
                        num4.set(Skill_timeData[3])
                        num5.set(Skill_timeData[4])
                        num6.set(Skill_timeData[5])
                        reduce_skill_cooltime.set(Skill_timeData[6])
                else:
                    Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                    store_all(preset)

    else:
        if preset == "1":
            if not os.path.exists("C:\ProDays"):
                os.makedirs("C:\ProDays")
            HotbarKeys = ["2", "3", "4", "5", "6", "7"]
            Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
            start_key = "f9"
            if "num1" in globals():
                num1.set(Skill_timeData[0])
                num2.set(Skill_timeData[1])
                num3.set(Skill_timeData[2])
                num4.set(Skill_timeData[3])
                num5.set(Skill_timeData[4])
                num6.set(Skill_timeData[5])
                reduce_skill_cooltime.set(Skill_timeData[6])
        else:
            Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
            num1.set(Skill_timeData[0])
            num2.set(Skill_timeData[1])
            num3.set(Skill_timeData[2])
            num4.set(Skill_timeData[3])
            num5.set(Skill_timeData[4])
            num6.set(Skill_timeData[5])
            reduce_skill_cooltime.set(Skill_timeData[6])
        store_all(preset)
    return start_key, HotbarKeys, Skill_timeData


start_key, HotbarKeys, Skill_timeData = data_load()


def start_macro():
    thread1 = threading.Thread(target=macro)
    thread1.start()
    # thread2 = threading.Thread(target=keyboard_is_pressed)
    # thread2.start()


def keyboard_clicked():
    while startkey_stored:
        if keyboard.is_pressed(start_key):
            global looping
            if len(looping) != 0:
                if looping[-1]:
                    looping[-1] = False
                else:
                    looping.append(True)
                    thread_macro = threading.Thread(target=macro, args= [len(looping)-1])
                    thread_macro.start()
            else:
                looping.append(True)
                thread_macro = threading.Thread(target=macro, args= [0])
                thread_macro.start()
            time.sleep(0.1)
        time.sleep(0.05)


thread_key = threading.Thread(target=keyboard_clicked, daemon=True)
thread_key.start()


window = Tk()


# window.title("ProDays Skill Macro")
window.title("Macro")
window.geometry("500x375+100+100")
# 500x300
window.resizable(False, False)


outtext = Label(
    window, text=f"1~6번 입력칸: 스킬 6개 쿨타임 입력 (0이면 사용안함)\n7번 입력칸: 스킬쿨타임감소 스텟 입력\n키보드 입력 -> 스킬 사용 순서대로 키 천천히 입력\n시작 설정 -> 매크로 시작 키 설정\n{start_key}키 -> 매크로 on/off")
outtext.pack()


global keys
keys = Label(
    window, text=", ".join(HotbarKeys))
keys.pack()


global num1, num2, num3, num4, num5, num6, reduce_skill_cooltime
num1 = DoubleVar()
num1.set(Skill_timeData[0])
num2 = DoubleVar()
num2.set(Skill_timeData[1])
num3 = DoubleVar()
num3.set(Skill_timeData[2])
num4 = DoubleVar()
num4.set(Skill_timeData[3])
num5 = DoubleVar()
num5.set(Skill_timeData[4])
num6 = DoubleVar()
num6.set(Skill_timeData[5])
reduce_skill_cooltime = IntVar()
reduce_skill_cooltime.set(Skill_timeData[6])


entry_num1 = Entry(window, textvariable=num1)
entry_num2 = Entry(window, textvariable=num2)
entry_num3 = Entry(window, textvariable=num3)
entry_num4 = Entry(window, textvariable=num4)
entry_num5 = Entry(window, textvariable=num5)
entry_num6 = Entry(window, textvariable=num6)
entry_num7 = Entry(window, textvariable=reduce_skill_cooltime)

entry_num1.pack()
entry_num2.pack()
entry_num3.pack()
entry_num4.pack()
entry_num5.pack()
entry_num6.pack()
entry_num7.pack()


combobox = Combobox(window, height=5, width=8, values=[
                    1, 2, 3, 4, 5], state="readonly")
combobox.current(0)
combobox.place(x=380, y=225)
combobox.bind("<<ComboboxSelected>>", run_dataload)


btn1 = Button(window, text="키보드 입력", width=10,
              command=lambda: threading.Thread(target=store_key).start())
btn1.place(x=10, y=325)


btn2 = Button(window, text="저장", width=10,
              command=lambda: store_all(combobox.get()))
btn2.place(x=380, y=325)


btn3 = Button(window, text="시작 설정", width=10,
              command=lambda: threading.Thread(target=store_startkey).start())
btn3.place(x=10, y=225)


window.mainloop()
