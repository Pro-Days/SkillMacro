# 모듈

from requests import get
from threading import Thread
from time import sleep
import os.path
from tkinter import Tk, Label, DoubleVar, IntVar, Entry, ttk, Button
from keyboard import read_key, press, is_pressed


# 함수 선언


def version_check():
    response = get("https://api.github.com/repos/pro-days/skillmacro/releases/latest")
    checked_version = response.json()["name"]
    global lastest
    if version == checked_version:
        lastest = True
    else:
        lastest = False
        global update_url
        update_url = response.json()["assets"][0]["browser_download_url"]


def store_all(preset):
    if "num1" in globals():
        (
            Skill_timeData[0],
            Skill_timeData[1],
            Skill_timeData[2],
            Skill_timeData[3],
            Skill_timeData[4],
            Skill_timeData[5],
            Skill_timeData[6],
        ) = (
            num1.get(),
            num2.get(),
            num3.get(),
            num4.get(),
            num5.get(),
            num6.get(),
            reduce_skill_cooltime.get(),
        )
    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                " ".join(HotbarKeys)
                + "\n"
                + f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n"
                + start_key
            )
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}"
            )


def store_key():
    preset = combobox.get()
    keys.config(text="[]")
    HotbarKeys = []
    for i in range(6):
        key = read_key()
        HotbarKeys.append(key)
        keys.config(text="[ " + ", ".join(HotbarKeys) + " ]")
        sleep(0.5)

    keys.config(text=", ".join(HotbarKeys))

    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                " ".join(HotbarKeys)
                + "\n"
                + f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n"
                + start_key
            )
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}"
            )


def store_startkey():
    preset = combobox.get()
    startkey_stored = False
    start_key = read_key()
    outtext.config(
        text=f"1~6번 입력칸: 스킬 6개 쿨타임 입력 (0이면 사용안함)\n7번 입력칸: 스킬쿨타임감소 스탯 입력\n키보드 입력 -> 스킬 사용 순서대로 키 천천히 입력\n시작 설정 -> 매크로 시작 키 설정\n{start_key}키 -> 매크로 on/off"
    )

    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                " ".join(HotbarKeys)
                + "\n"
                + f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n"
                + start_key
            )
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}"
            )
    sleep(0.2)
    startkey_stored = True
    thread_key = Thread(target=keyboard_clicked, daemon=True)
    thread_key.start()


def loop1(n):
    sleep(num1.get() * (100 - reduce_skill_cooltime.get()) / 100 + 0.075)
    press_key[n].append(0)


def loop2(n):
    sleep(num2.get() * (100 - reduce_skill_cooltime.get()) / 100 + 0.075)
    press_key[n].append(1)


def loop3(n):
    sleep(num3.get() * (100 - reduce_skill_cooltime.get()) / 100 + 0.075)
    press_key[n].append(2)


def loop4(n):
    sleep(num4.get() * (100 - reduce_skill_cooltime.get()) / 100 + 0.075)
    press_key[n].append(3)


def loop5(n):
    sleep(num5.get() * (100 - reduce_skill_cooltime.get()) / 100 + 0.075)
    press_key[n].append(4)


def loop6(n):
    sleep(num6.get() * (100 - reduce_skill_cooltime.get()) / 100 + 0.075)
    press_key[n].append(5)


def macro(n):
    press_key.append([])

    if looping[n] and num1.get() != 0:
        skill1 = Thread(target=loop1, args=[n])
        skill1.start()
        press(HotbarKeys[0])
        sleep(delay)

    if looping[n] and num2.get() != 0:
        skill2 = Thread(target=loop2, args=[n])
        skill2.start()
        press(HotbarKeys[1])
        sleep(delay)

    if looping[n] and num3.get() != 0:
        skill3 = Thread(target=loop3, args=[n])
        skill3.start()
        press(HotbarKeys[2])
        sleep(delay)

    if looping[n] and num4.get() != 0:
        skill4 = Thread(target=loop4, args=[n])
        skill4.start()
        press(HotbarKeys[3])
        sleep(delay)

    if looping[n] and num5.get() != 0:
        skill5 = Thread(target=loop5, args=[n])
        skill5.start()
        press(HotbarKeys[4])
        sleep(delay)

    if looping[n] and num6.get() != 0:
        skill6 = Thread(target=loop6, args=[n])
        skill6.start()
        press(HotbarKeys[5])
        sleep(delay)

    while looping[n]:
        if press_key[n]:
            press_key[n].sort()
            press(HotbarKeys[press_key[n][0]])
            if press_key[n][0] == 0:
                t = Thread(target=loop1, args=[n])
            elif press_key[n][0] == 1:
                t = Thread(target=loop2, args=[n])
            elif press_key[n][0] == 2:
                t = Thread(target=loop3, args=[n])
            elif press_key[n][0] == 3:
                t = Thread(target=loop4, args=[n])
            elif press_key[n][0] == 4:
                t = Thread(target=loop5, args=[n])
            elif press_key[n][0] == 5:
                t = Thread(target=loop6, args=[n])
            t.start()
            del press_key[n][0]
        sleep(delay)


def run_dataload(event):
    data_load()


def data_load():
    preset = combobox.get() if "combobox" in globals() else "1"

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


def start_macro():
    thread1 = Thread(target=macro)
    thread1.start()


def keyboard_clicked():
    while startkey_stored:
        if is_pressed(start_key):
            if len(looping) != 0:
                if looping[-1]:
                    looping[-1] = False
                else:
                    looping.append(True)
                    thread_macro = Thread(target=macro, args=[len(looping) - 1])
                    thread_macro.start()
            else:
                looping.append(True)
                thread_macro = Thread(target=macro, args=[0])
                thread_macro.start()
            sleep(0.1)
        sleep(0.05)


# 변수 선언, main

version = "v7.0"
looping = []
delay = 0.15
startkey_stored = True
press_key = []

start_key, HotbarKeys, Skill_timeData = data_load()


thread_key = Thread(target=keyboard_clicked, daemon=True)
thread_key.start()


window = Tk()

window.title("Macro")
window.geometry("400x300+100+100")
window.resizable(False, False)


outtext = Label(
    window,
    text=f"1~6번 입력칸: 스킬 6개 쿨타임 입력 (0이면 사용안함)\n7번 입력칸: 스킬쿨타임감소 스탯 입력\n키보드 입력 -> 스킬 사용 순서대로 키 천천히 입력\n시작 설정 -> 매크로 시작 키 설정\n{start_key}키 -> 매크로 on/off",
)
outtext.pack()


keys = Label(window, text=", ".join(HotbarKeys))
keys.pack()


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


combobox = ttk.Combobox(
    window, height=5, width=8, values=[1, 2, 3, 4, 5], state="readonly"
)
combobox.current(0)
combobox.place(x=280, y=200)
combobox.bind("<<ComboboxSelected>>", run_dataload)


btn1 = Button(
    window,
    text="키보드 입력",
    width=10,
    command=lambda: Thread(target=store_key).start(),
)
btn1.place(x=10, y=275)


btn2 = Button(window, text="저장", width=10, command=lambda: store_all(combobox.get()))
btn2.place(x=280, y=275)


btn3 = Button(
    window,
    text="시작 설정",
    width=10,
    command=lambda: Thread(target=store_startkey).start(),
)
btn3.place(x=10, y=200)


window.mainloop()
