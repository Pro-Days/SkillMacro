# 모듈

from requests import get
from threading import Thread
from time import sleep
import os.path
from tkinter import Tk, Label, DoubleVar, IntVar, StringVar, Entry, ttk, Button, Frame, font
from keyboard import read_key, is_pressed
from pyautogui import press
from webbrowser import open_new


# 함수 선언

def version_check():
    response = get(
        "https://api.github.com/repos/pro-days/skillmacro/releases/latest")
    checked_version = response.json()["name"]
    global lastest
    if version == checked_version:
        lastest = True
    else:
        lastest = False
        global update_url
        update_url = response.json()["assets"][0]["browser_download_url"]


def store_all(preset):
    global Skill_timeData, HotbarKeys, delaytime, start_key
    if "num1" in globals() and num1 != None:
        Skill_timeData, delaytime = [num1.get(), num2.get(), num3.get(), num4.get(
        ), num5.get(), num6.get(), reduce_skill_cooltime.get()], delay.get()

        HotbarKeys = [keys1.get(), keys2.get(), keys3.get(),
                      keys4.get(), keys5.get(), keys6.get()]
    if preset == "1":
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(" ".join(HotbarKeys) + "\n" +
                    f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n" + start_key + "\n" + str(delaytime))
    else:
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}")


def store_startkey():
    global start_key, startkey_stored
    preset = combobox.get()
    startkey_stored = False
    start_key = read_key()

    with open(f"C:\ProDays\PD_SkillMacro1.txt", "w") as f:
        f.write(" ".join(HotbarKeys) + "\n" +
                f"{Skill_timeData[0]} {Skill_timeData[1]} {Skill_timeData[2]} {Skill_timeData[3]} {Skill_timeData[4]} {Skill_timeData[5]} {Skill_timeData[6]}\n" + start_key + "\n" + str(delaytime))
    sleep(0.2)
    startkey_stored = True
    thread_key = Thread(target=keyboard_clicked, daemon=True)
    thread_key.start()
    startkey_button.config(text=start_key)


def loop1(n):
    sleep(num1.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(0)


def loop2(n):
    sleep(num2.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(1)


def loop3(n):
    sleep(num3.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(2)


def loop4(n):
    sleep(num4.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(3)


def loop5(n):
    sleep(num5.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(4)


def loop6(n):
    sleep(num6.get() * (100-reduce_skill_cooltime.get())/100 + 0.075)
    press_key[n].append(5)


def macro(n):
    press_key.append([])

    if looping[n] and num1.get() != 0:
        skill1 = Thread(target=loop1, args=[n])
        skill1.start()
        press(keys1.get())
        sleep(delay.get()/100)

    if looping[n] and num2.get() != 0:
        skill2 = Thread(target=loop2, args=[n])
        skill2.start()
        press(keys2.get())
        sleep(delay.get()/100)

    if looping[n] and num3.get() != 0:
        skill3 = Thread(target=loop3, args=[n])
        skill3.start()
        press(keys3.get())
        sleep(delay.get()/100)

    if looping[n] and num4.get() != 0:
        skill4 = Thread(target=loop4, args=[n])
        skill4.start()
        press(keys4.get())
        sleep(delay.get()/100)

    if looping[n] and num5.get() != 0:
        skill5 = Thread(target=loop5, args=[n])
        skill5.start()
        press(keys5.get())
        sleep(delay.get()/100)

    if looping[n] and num6.get() != 0:
        skill6 = Thread(target=loop6, args=[n])
        skill6.start()
        press(keys6.get())
        sleep(delay.get()/100)

    while looping[n]:
        if press_key[n]:
            press_key[n].sort()
            if press_key[n][0] == 0:
                press(keys1.get())
                t = Thread(target=loop1, args=[n])
            elif press_key[n][0] == 1:
                press(keys2.get())
                t = Thread(target=loop2, args=[n])
            elif press_key[n][0] == 2:
                press(keys3.get())
                t = Thread(target=loop3, args=[n])
            elif press_key[n][0] == 3:
                press(keys4.get())
                t = Thread(target=loop4, args=[n])
            elif press_key[n][0] == 4:
                press(keys5.get())
                t = Thread(target=loop5, args=[n])
            elif press_key[n][0] == 5:
                press(keys6.get())
                t = Thread(target=loop6, args=[n])
            t.start()
            del press_key[n][0]
        sleep(delay.get()/100)


def run_dataload(event):
    data_load()


def data_load():
    global HotbarKeys, Skill_timeData, start_key, delaytime
    preset = combobox.get() if "combobox" in globals() else "1"

    if os.path.isfile(f"C:\ProDays\PD_SkillMacro{preset}.txt"):
        with open(f"C:\ProDays\PD_SkillMacro{preset}.txt", "r") as f:
            text = f.readlines()
            if preset == "1":
                if len(text) == 4:
                    SkillData = text[0].replace("\n", "")
                    HotbarKeys = SkillData.replace("\n", "").split(" ")
                    if len(HotbarKeys) != 6:
                        HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                    Skill_timeData = text[1].replace("\n", "")
                    Skill_timeData = Skill_timeData.split(" ")

                    if len(Skill_timeData) != 7:
                        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                    start_key = text[2].replace("\n", "")
                    delaytime = int(text[3].replace("\n", ""))

                    if "num1" in globals() and num1 != None:
                        num1.set(Skill_timeData[0])
                        num2.set(Skill_timeData[1])
                        num3.set(Skill_timeData[2])
                        num4.set(Skill_timeData[3])
                        num5.set(Skill_timeData[4])
                        num6.set(Skill_timeData[5])
                        reduce_skill_cooltime.set(Skill_timeData[6])
                        delay.set(delaytime)
                else:
                    HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                    Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                    start_key = "f9"
                    delaytime = 15
                    store_all(preset)
            else:
                if len(text) == 1:
                    Skill_timeData = text[0].replace("\n", "")
                    Skill_timeData = Skill_timeData.split(" ")

                    if len(Skill_timeData) != 7:
                        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]

                    if "num1" in globals() and num1 != None:
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
            delaytime = 15
            if "num1" in globals() and num1 != None:
                num1.set(Skill_timeData[0])
                num2.set(Skill_timeData[1])
                num3.set(Skill_timeData[2])
                num4.set(Skill_timeData[3])
                num5.set(Skill_timeData[4])
                num6.set(Skill_timeData[5])
                reduce_skill_cooltime.set(Skill_timeData[6])
                delay.set(delaytime)
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


def start_macro():
    thread1 = Thread(target=macro)
    thread1.start()


def keyboard_clicked():
    while startkey_stored:
        if is_pressed(start_key):
            if len(looping) != 0:
                if looping[-1]:
                    looping[-1] = False
                    running_label.config(text="실행중: X", fg="green")
                else:
                    looping.append(True)
                    thread_macro = Thread(
                        target=macro, args=[len(looping)-1])
                    thread_macro.start()
                    running_label.config(text="실행중: O", fg="red")
            else:
                looping.append(True)
                thread_macro = Thread(target=macro, args=[0])
                thread_macro.start()
                running_label.config(text="실행중: O", fg="red")
            sleep(0.2)
        sleep(0.05)


def check_error():
    global error
    while True:
        try:
            delay.get()
            reduce_skill_cooltime.get()
            num1.get()
            num2.get()
            num3.get()
            num4.get()
            num5.get()
            num6.get()
            is_pressed(keys1.get())
            is_pressed(keys2.get())
            is_pressed(keys3.get())
            is_pressed(keys4.get())
            is_pressed(keys5.get())
            is_pressed(keys6.get())
        except:
            error = True
            error_label.config(text="오류: O", fg="red")
        else:
            if 0 <= reduce_skill_cooltime.get() <= 99:
                error = True
                error_label.config(text="오류: X", fg="green")
            else:
                error_label.config(text="오류: O", fg="red")

        sleep(0.5)


# 변수 선언, main
version = "v7.0"
looping = []
startkey_stored = True
press_key = []
error = False
num1 = num2 = num3 = num4 = num5 = num6 = keys1 = keys2 = keys3 = keys4 = keys5 = keys6 = None


data_load()


thread_key = Thread(target=keyboard_clicked, daemon=True)
thread_key.start()


version_check()


window = Tk()


window.title("데이즈매크로 v7.0")
window.geometry("540x375+100+100")
window.resizable(False, False)
window.iconbitmap("icon.ico")


# 업데이트 체크
frame_update = Frame(window, width=270, height=45)
frame_update.pack_propagate(0)
frame_update.place(x=0, y=0)

update_label = Label(frame_update, text="최신버전 X (클릭)", fg="red", borderwidth=1.5, relief="solid",
                     font=("맑은 고딕", 12, "bold"), width=20, height=10)
update_label.pack()
update_label.bind("<Button-1>", lambda event: open_new(update_url))
if lastest:
    update_label.config(text="최신버전 O", fg="green")


# 설명 링크
frame_descr = Frame(window, width=270, height=45)
frame_descr.pack_propagate(0)
frame_descr.place(x=270, y=0)

descr_label = Label(frame_descr, text="설명 확인하기", fg="blue", borderwidth=1.5, relief="solid",
                    font=("맑은 고딕", 12, "bold"), width=20, height=10)
descr_label.pack()
descr_label.bind(
    "<Button-1>", lambda event: open_new("https://github.com/Pro-Days/SkillMacro#readme"))


# 설정 프레임
frame_settings = Frame(window, width=270, height=330)
frame_settings.pack_propagate(0)
frame_settings.place(x=0, y=45)


# 딜레이
frame_delayT = Frame(frame_settings, width=112.5, height=37.5)
frame_delayT.pack_propagate(0)
frame_delayT.place(x=15, y=15)

Label(frame_delayT, text="딜레이", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_delayN = Frame(frame_settings, width=112.5, height=37.5)
frame_delayN.pack_propagate(0)
frame_delayN.place(x=142.5, y=15)

delay = IntVar()
delay.set(delaytime)
Entry(frame_delayN, textvariable=delay, fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10)).place(width=112.5, height=37.5)


# 쿨타임감소
frame_rscT = Frame(frame_settings, width=112.5, height=37.5)
frame_rscT.pack_propagate(0)
frame_rscT.place(x=15, y=67.5)

Label(frame_rscT, text="쿨타임감소", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_rscN = Frame(frame_settings, width=112.5, height=37.5)
frame_rscN.pack_propagate(0)
frame_rscN.place(x=142.5, y=67.5)

reduce_skill_cooltime = IntVar()
reduce_skill_cooltime.set(Skill_timeData[6])
Entry(frame_rscN, textvariable=reduce_skill_cooltime, fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10)).place(width=112.5, height=37.5)


# 시작키설정
frame_startkeyT = Frame(frame_settings, width=112.5, height=37.5)
frame_startkeyT.pack_propagate(0)
frame_startkeyT.place(x=15, y=120)

Label(frame_startkeyT, text="시작키설정", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_startkeyK = Frame(frame_settings, width=112.5, height=37.5)
frame_startkeyK.pack_propagate(0)
frame_startkeyK.place(x=142.5, y=120)

startkey_button = Button(frame_startkeyK, text=start_key, width=10, borderwidth=1, relief="solid", font=("맑은 고딕", 10), bg="white", anchor="center",
                         command=store_startkey)
startkey_button.pack()


# 프리셋
frame_presetT = Frame(frame_settings, width=112.5, height=37.5)
frame_presetT.pack_propagate(0)
frame_presetT.place(x=15, y=172.5)

Label(frame_presetT, text="프리셋", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_presetN = Frame(frame_settings, width=112.5, height=37.5)
frame_presetN.pack_propagate(0)
frame_presetN.place(x=142.5, y=172.5)

combobox = ttk.Combobox(frame_presetN, font=("맑은 고딕", 10), values=[
    1, 2, 3, 4, 5], state="readonly", justify="center")
combobox.current(0)
combobox.place(width=112.5, height=37.5)
combobox.bind("<<ComboboxSelected>>", run_dataload)


# 저장
frame_store = Frame(frame_settings, width=112.5, height=37.5)
frame_store.pack_propagate(0)
frame_store.place(x=78.75, y=225)

Button(frame_store, text="저장", width=10, borderwidth=1, relief="solid", font=("맑은 고딕", 10), bg="white", anchor="center",
       command=lambda: store_all(combobox.get())).pack()


# 정보표시
frame_runnung = Frame(frame_settings, width=112.5, height=37.5)
frame_runnung.pack_propagate(0)
frame_runnung.place(x=15, y=277.5)

if len(looping) != 0 and looping[-1]:
    running_label = Label(frame_runnung, text="실행중: O", fg="red", borderwidth=1, relief="solid",
                          font=("맑은 고딕", 10), width=20, height=10)
    running_label.pack()
else:
    running_label = Label(frame_runnung, text="실행중: X", fg="green", borderwidth=1, relief="solid",
                          font=("맑은 고딕", 10), width=20, height=10)
    running_label.pack()


frame_error = Frame(frame_settings, width=112.5, height=37.5)
frame_error.pack_propagate(0)
frame_error.place(x=142.5, y=277.5)

error_label = Label(frame_error, text="오류: X", fg="green", borderwidth=1, relief="solid",
                    font=("맑은 고딕", 10), width=20, height=10)
error_label.pack()


# 스킬 프레임
frame_skills = Frame(window, width=270, height=330)
frame_skills.pack_propagate(0)
frame_skills.place(x=270, y=45)


# 스킬
for i in range(1, 7):
    globals()[f"frame_{i}skillK"] = Frame(
        frame_skills, width=112.5, height=37.5)
    globals()[f"frame_{i}skillK"].pack_propagate(0)
    globals()[f"frame_{i}skillK"].place(x=15, y=15 + (i-1) * 52.5)

    globals()[f"keys{i}"] = StringVar()
    globals()[f"keys{i}"].set(HotbarKeys[i-1])
    Entry(globals()[f"frame_{i}skillK"], textvariable=globals()[f"keys{i}"], fg="black", borderwidth=1, relief="solid", justify="center",
          font=("맑은 고딕", 10)).place(width=80, height=37.5)

    globals()[f"frame_{i}skillN"] = Frame(
        frame_skills, width=145, height=37.55)
    globals()[f"frame_{i}skillN"].pack_propagate(0)
    globals()[f"frame_{i}skillN"].place(x=110, y=15 + (i-1) * 52.5)

    globals()[f"num{i}"] = DoubleVar()
    globals()[f"num{i}"].set(Skill_timeData[i-1])
    Entry(globals()[f"frame_{i}skillN"], textvariable=globals()[f"num{i}"], fg="black", borderwidth=1, relief="solid",
          font=("맑은 고딕", 10)).place(width=145, height=37.5)


thread_error = Thread(target=check_error, daemon=True)
thread_error.start()


window.mainloop()
