# 모듈

import sys
from requests import get
from threading import Thread
from time import sleep
import os.path
import tkinter as tk
from tkinter import (
    Tk,
    Label,
    DoubleVar,
    IntVar,
    StringVar,
    Entry,
    ttk,
    Button,
    Frame,
    font,
    SUNKEN,
    BOTTOM,
    RIDGE,
    Checkbutton,
)
from keyboard import read_key, is_pressed, press
from pyautogui import click
from webbrowser import open_new
import json


# 함수 선언
def version_check():
    try:
        response = get(
            "https://api.github.com/repos/pro-days/skillmacro/releases/latest"
        )
        checked_version = response.json()["name"]
        if response.status_code == 200:
            if version == checked_version:
                update_label.config(text="최신버전 O", fg="green")
            else:
                update_url = response.json()["html_url"]
                update_label.bind("<Button-1>", lambda event: open_new(update_url))
                update_label.config(text="최신버전 X", fg="red")
        else:
            update_label.config(text="업데이트 확인 실패", fg="red")
    except:
        update_label.config(text="업데이트 확인 실패", fg="red")


def store_all(preset):
    global Skill_timeData, HotbarKeys, start_key, clicknums, reduce_skill_cooltime

    Skill_timeData = [i.get() for i in nums_DV]
    Skill_timeData.append(reduce_skill_cooltime.get())

    HotbarKeys = [i.get() for i in keys_SV]
    clicknums = [i.get() for i in clicks_IV]

    should_click = CheckVar.get()

    with open("C:\\ProDays\\DaysMacro.json", "r") as f:
        json_object = json.load(f)

    json_object["HotbarKeys"] = HotbarKeys
    json_object["Skill_timeData"][str(preset)] = Skill_timeData[:-1]
    json_object["reduce_skill_cooltime"][str(preset)] = Skill_timeData[-1]
    json_object["delaytime"] = delay.get()
    json_object["clicknums"][str(preset)] = clicknums
    json_object["should_click"][int(preset) - 1] = should_click
    json_object["mode"][int(preset) - 1] = int(combobox_mode.get()[-1])

    with open("C:\\ProDays\\DaysMacro.json", "w") as f:
        json.dump(json_object, f)


def store_startkey():
    global start_key, startkey_stored
    startkey_stored = False
    start_key = read_key()

    with open("C:\\ProDays\\DaysMacro.json", "r") as f:
        json_object = json.load(f)
    json_object["start_key"] = start_key

    with open("C:\\ProDays\\DaysMacro.json", "w") as f:
        json.dump(json_object, f)

    sleep(0.2)
    startkey_stored = True
    thread_key = Thread(target=keyboard_clicked, daemon=True)
    thread_key.start()
    startkey_button.config(text=start_key)


def loop(ln, n):
    sleep(
        nums_DV[ln].get() * (100 - reduce_skill_cooltime.get()) / 100
        + delay.get() / 200
    )
    press_key[n].append(ln)


def timer(n):
    global sec
    while looping[n]:
        sec += 1


def afk(n):
    global sec
    sec = 0
    Thread(target=timer, args=[n]).start()
    while looping[n]:
        key = read_key()
        keys_list = [keys_SV[i].get() for i in range(6)]
        if not key in keys_list:
            sec = 0
            # print("sec += 1")
        if sec == 100:
            # print("sec == 5")
            looping[n] = False
            running_label.config(text="실행중: X", fg="green")


def macro(n):
    # click{n} == 0: thread.start()

    press_key.append([])
    m = combobox_mode.get() == "모드 2"
    c = CheckVar.get()

    for i in range(6):
        press_key[n].append(i)

    # Thread(target=afk, args=[n]).start()

    while looping[n]:
        if c:
            click()
            if press_key[n]:
                # press_key[n].sort()
                for idx in range(6):
                    if press_key[n][0] == idx:
                        press(keys_SV[idx].get())
                        if m:  # 클릭 딜레이 따로 만들기
                            if clicks_IV[idx].get() != 0:
                                for i in range(clicks_IV[idx].get()):
                                    sleep(delay.get() / 100)
                                    if looping[n]:
                                        click()
                                        if i == 0:
                                            Thread(target=loop, args=[idx, n]).start()
                                    else:
                                        break
                            else:
                                Thread(target=loop, args=[idx, n]).start()
                                # click()
                                sleep(delay.get() / 100)
                        else:
                            Thread(target=loop, args=[idx, n]).start()
                            # click()
                            sleep(delay.get() / 100)
                del press_key[n][0]
            else:
                # click()
                sleep(delay.get() / 500)
        else:
            if press_key[n]:
                # press_key[n].sort()
                for idx in range(6):
                    if press_key[n][0] == idx:
                        press(keys_SV[idx].get())
                        if m:
                            if clicks_IV[idx].get() != 0:
                                for i in range(clicks_IV[idx].get()):
                                    sleep(delay.get() / 100)
                                    if looping[n]:
                                        click()
                                        if i == 0:
                                            Thread(target=loop, args=[idx, n]).start()
                                    else:
                                        break
                            else:
                                Thread(target=loop, args=[idx, n]).start()
                                sleep(delay.get() / 100)
                        else:
                            Thread(target=loop, args=[idx, n]).start()
                            sleep(delay.get() / 100)
                del press_key[n][0]
            else:
                sleep(delay.get() / 500)


def data_update(error, json_object):
    print(error)
    global HotbarKeys, Skill_timeData, clicknums, should_click, mode, delaytime, start_key
    if "HotbarKeys" in error:
        json_object["HotbarKeys"] = ["2", "3", "4", "5", "6", "7"]
        HotbarKeys = ["2", "3", "4", "5", "6", "7"]
    if "Skill_timeData" in error:
        json_object["Skill_timeData"] = {
            "1": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "2": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "3": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "4": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "5": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }
        json_object["reduce_skill_cooltime"] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
    if "start_key" in error:
        json_object["start_key"] = "f9"
        start_key = "f9"
    if "delaytime" in error:
        json_object["delaytime"] = 15
        delaytime = 15
    if "clicknums" in error:
        json_object["clicknums"] = {
            "1": [1, 1, 1, 1, 1, 1],
            "2": [1, 1, 1, 1, 1, 1],
            "3": [1, 1, 1, 1, 1, 1],
            "4": [1, 1, 1, 1, 1, 1],
            "5": [1, 1, 1, 1, 1, 1],
        }
        clicknums = [1, 1, 1, 1, 1, 1]
    if "should_click" in error:
        json_object["should_click"] = [0, 0, 0, 0, 0]
        should_click = 0
    if "mode" in error:
        json_object["mode"] = [1, 1, 1, 1, 1]
        mode = 1

    with open("C:\\ProDays\\DaysMacro.json", "w") as f:
        json.dump(json_object, f)


def dataload(event, setup=False):
    global HotbarKeys, Skill_timeData, start_key, delaytime, clicknums, should_click, mode
    preset = combobox_preset.get()[-1] if "combobox_preset" in globals() else "1"

    error = []

    if os.path.isfile("C:\\ProDays\\DaysMacro.json"):
        with open("C:\\ProDays\\DaysMacro.json", "r") as f:
            json_object = json.load(f)

            try:
                HotbarKeys = json_object["HotbarKeys"]
            except:
                error.append("HotbarKeys")
            else:
                if len(HotbarKeys) != 6:
                    error.append("HotbarKeys")
            try:
                Skill_timeData = json_object["Skill_timeData"][str(preset)]
                Skill_timeData.append(json_object["reduce_skill_cooltime"][str(preset)])
            except:
                error.append("Skill_timeData")
            else:
                if len(Skill_timeData) != 7:
                    error.append("Skill_timeData")
            try:
                start_key = json_object["start_key"]
            except:
                error.append("start_key")
            try:
                delaytime = json_object["delaytime"]
            except:
                error.append("delaytime")
            try:
                clicknums = json_object["clicknums"][str(preset)]
            except:
                error.append("clicknums")
            else:
                if len(clicknums) != 6:
                    error.append("clicknums")
            try:
                should_click = json_object["should_click"][int(preset) - 1]
            except:
                error.append("should_click")
            else:
                if should_click != 0 and should_click != 1:
                    error.append("should_click")
            try:
                mode = json_object["mode"][int(preset) - 1]
            except:
                error.append("mode")
            else:
                if mode != 1 and mode != 2:
                    error.append("mode")

            if error:
                # os.remove("C:\\ProDays\\DaysMacro.json")
                data_update(error, json_object)
                return

            if not setup:
                for i, j in enumerate(nums_DV):
                    j.set(float(Skill_timeData[i]))
                reduce_skill_cooltime.set(int(Skill_timeData[-1]))
                for i, j in enumerate(clicks_IV):
                    j.set(int(clicknums[i]))
                if should_click:
                    click_check.select()
                else:
                    click_check.deselect()
                if mode == 1:
                    combobox_mode.current(0)
                else:
                    combobox_mode.current(1)
    else:
        if not os.path.exists("C:\\ProDays"):
            os.makedirs("C:\\ProDays")

        json_object = {
            "HotbarKeys": ["2", "3", "4", "5", "6", "7"],
            "Skill_timeData": {
                "1": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "2": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "3": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "4": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "5": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            "reduce_skill_cooltime": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "start_key": "f9",
            "delaytime": 15,
            "clicknums": {
                "1": [1, 1, 1, 1, 1, 1],
                "2": [1, 1, 1, 1, 1, 1],
                "3": [1, 1, 1, 1, 1, 1],
                "4": [1, 1, 1, 1, 1, 1],
                "5": [1, 1, 1, 1, 1, 1],
            },
            "should_click": [0, 0, 0, 0, 0],
            "mode": [1, 1, 1, 1, 1],
        }

        with open("C:\\ProDays\\DaysMacro.json", "w") as f:
            json.dump(json_object, f)

        HotbarKeys = ["2", "3", "4", "5", "6", "7"]
        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
        start_key = "f9"
        delaytime = 15
        clicknums = [1, 1, 1, 1, 1, 1]
        should_click = 0
        mode = 1


def start_macro():
    thread1 = Thread(target=macro)
    thread1.start()


def keyboard_clicked():
    while startkey_stored:
        key = read_key()
        if key == "f9" and not error:
            if len(looping) != 0:
                # print(looping[-1])
                if looping[-1]:
                    looping[-1] = False
                    running_label.config(text="실행중: X", fg="green")
                else:
                    looping.append(True)
                    thread_macro = Thread(target=macro, args=[len(looping) - 1])
                    thread_macro.start()
                    running_label.config(text="실행중: O", fg="red")
            else:
                looping.append(True)
                thread_macro = Thread(target=macro, args=[0])
                thread_macro.start()
                running_label.config(text="실행중: O", fg="red")
            sleep(0.2)


def check_error():
    global error
    while True:
        try:
            delay.get()
            reduce_skill_cooltime.get()
            for i in nums_DV:
                i.get()
            for i in keys_SV:
                is_pressed(i.get())
            for i in clicks_IV:
                i.get()
        except:
            error = True
            error_label.config(text="오류: O", fg="red")
        else:
            if 0 <= reduce_skill_cooltime.get() <= 99:
                error = False
                error_label.config(text="오류: X", fg="green")
            else:
                error = True
                error_label.config(text="오류: O", fg="red")

        sleep(0.5)


def modechange(event):
    if combobox_mode.get() == "모드 1":
        for i in range(1, 7):
            globals()[f"frame_{i}skillK"].config(width=112.5, height=37.5)
            globals()[f"entry_key{i}"].place(width=80, height=37.5)

            globals()[f"frame_{i}skillN"].config(width=145, height=37.5)
            globals()[f"frame_{i}skillN"].place(x=110, y=15 + (i - 1) * 52.5)
            globals()[f"entry_num{i}"].place(width=145, height=37.5)

            globals()[f"frame_{i}skillC"].place_forget()
    else:
        for i in range(1, 7):
            globals()[f"frame_{i}skillK"].config(width=60)
            globals()[f"entry_key{i}"].place(width=60, height=37.5)

            globals()[f"frame_{i}skillN"].config(width=90)
            globals()[f"frame_{i}skillN"].place(x=90, y=15 + (i - 1) * 52.5)
            globals()[f"entry_num{i}"].place(width=90, height=37.5)

            globals()[f"frame_{i}skillC"].place(x=195, y=15 + (i - 1) * 52.5)


# 변수 선언, main

version = "v2.2.0"
looping = []
startkey_stored = True
press_key = []
error = False


dataload(None, setup=True)


thread_key = Thread(target=keyboard_clicked, daemon=True)
thread_key.start()


window = Tk()


window.title("데이즈 스킬매크로 " + version)
window.geometry("540x400")
window.resizable(False, False)


# 리스트 속에 배치
nums_DV = [DoubleVar() for i in range(6)]
# num1, num2, num3, num4, num5, num6 = [DoubleVar() for i in range(6)]
keys_SV = [StringVar() for i in range(6)]
# keys1, keys2, keys3, keys4, keys5, keys6 = [StringVar() for i in range(6)]
clicks_IV = [IntVar() for i in range(6)]
# click1, click2, click3, click4, click5, click6 = [IntVar() for i in range(6)]


try:
    os.chdir(sys._MEIPASS)
    # print(sys._MEIPASS)
except:
    os.chdir(os.getcwd())
window.iconbitmap(default="icon.ico")


# 업데이트 체크
frame_update = Frame(window, width=270, height=45)
frame_update.pack_propagate(False)
frame_update.place(x=0, y=0)

update_label = Label(
    frame_update,
    text="업데이트 확인중...",
    fg="gray",
    relief="solid",
    font=("맑은 고딕", 14, "bold"),
    width=30,
    height=20,
    borderwidth=1.5,
)
update_label.pack()

thread_version = Thread(target=version_check, daemon=True)
thread_version.start()


# 설명 링크
frame_descr = Frame(window, width=270, height=45)
frame_descr.pack_propagate(False)
frame_descr.place(x=270, y=0)

descr_label = Label(
    frame_descr,
    text="설명 확인하기",
    fg="blue",
    borderwidth=1.5,
    relief="solid",
    font=("맑은 고딕", 14, "bold"),
    width=30,
    height=20,
)
descr_label.pack()
descr_label.bind(
    "<Button-1>",
    lambda event: open_new("https://github.com/Pro-Days/SkillMacro#readme"),
)


# 설정 프레임
frame_settings = Frame(window, width=270, height=330)
frame_settings.pack_propagate(False)
frame_settings.place(x=0, y=45)


# 딜레이
frame_delayT = Frame(frame_settings, width=112.5, height=37.5)
frame_delayT.pack_propagate(False)
frame_delayT.place(x=15, y=15)

Label(
    frame_delayT,
    text="딜레이",
    fg="black",
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
    width=20,
    height=10,
).pack()


frame_delayN = Frame(frame_settings, width=112.5, height=37.5)
frame_delayN.pack_propagate(False)
frame_delayN.place(x=142.5, y=15)

delay = IntVar()
delay.set(delaytime)
Entry(
    frame_delayN,
    textvariable=delay,
    fg="black",
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
).place(width=112.5, height=37.5)


# 쿨타임감소
frame_rscT = Frame(frame_settings, width=112.5, height=37.5)
frame_rscT.pack_propagate(False)
frame_rscT.place(x=15, y=67.5)

Label(
    frame_rscT,
    text="쿨타임감소",
    fg="black",
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
    width=20,
    height=10,
).pack()


frame_rscN = Frame(frame_settings, width=112.5, height=37.5)
frame_rscN.pack_propagate(False)
frame_rscN.place(x=142.5, y=67.5)

reduce_skill_cooltime = IntVar()
reduce_skill_cooltime.set(int(Skill_timeData[6]))
Entry(
    frame_rscN,
    textvariable=reduce_skill_cooltime,
    fg="black",
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
).place(width=112.5, height=37.5)


# 시작키설정
frame_startkeyT = Frame(frame_settings, width=112.5, height=37.5)
frame_startkeyT.pack_propagate(False)
frame_startkeyT.place(x=15, y=120)

Label(
    frame_startkeyT,
    text="시작키설정",
    fg="black",
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
    width=20,
    height=10,
).pack()


frame_startkeyK = Frame(frame_settings, width=112.5, height=37.5)
frame_startkeyK.pack_propagate(False)
frame_startkeyK.place(x=142.5, y=120)

startkey_button = Button(
    frame_startkeyK,
    text=start_key,
    width=10,
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
    bg="white",
    anchor="center",
    command=store_startkey,
)
startkey_button.place(width=112.5, height=37.5)


# 마우스 클릭
frame_click = Frame(frame_settings, width=112.5, height=37.5)
frame_click.pack_propagate(False)
frame_click.place(x=15, y=172.5)

CheckVar = IntVar()
click_check = Checkbutton(
    frame_click,
    text="마우스 클릭",
    variable=CheckVar,
    font=("맑은 고딕", 10),
    relief="solid",
    borderwidth=1,
)
click_check.place(width=112.5, height=37.5)
if should_click:
    click_check.select()
else:
    click_check.deselect()


# 프리셋
frame_presetN = Frame(frame_settings, width=112.5, height=37.5)
frame_presetN.pack_propagate(False)
frame_presetN.place(x=142.5, y=172.5)

combobox_preset = ttk.Combobox(
    frame_presetN,
    font=("맑은 고딕", 10),
    values=["프리셋 1", "프리셋 2", "프리셋 3", "프리셋 4", "프리셋 5"],
    state="readonly",
    justify="center",
)
combobox_preset.current(0)
combobox_preset.place(width=112.5, height=37.5)
combobox_preset.bind("<<ComboboxSelected>>", dataload)


# 저장 & 모드
frame_store = Frame(frame_settings, width=112.5, height=37.5)
frame_store.pack_propagate(False)
frame_store.place(x=15, y=225)

Button(
    frame_store,
    text="저장",
    width=10,
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
    bg="white",
    anchor="center",
    command=lambda: store_all(combobox_preset.get()[-1]),
).place(width=112.5, height=37.5)


frame_mode = Frame(frame_settings, width=112.5, height=37.5)
frame_mode.pack_propagate(False)
frame_mode.place(x=142.5, y=225)

combobox_mode = ttk.Combobox(
    frame_mode,
    font=("맑은 고딕", 10),
    values=["모드 1", "모드 2"],
    state="readonly",
    justify="center",
)
combobox_mode.current(mode - 1)
combobox_mode.place(width=112.5, height=37.5)
combobox_mode.bind("<<ComboboxSelected>>", modechange)


# 정보표시
frame_runnung = Frame(frame_settings, width=112.5, height=37.5)
frame_runnung.pack_propagate(False)
frame_runnung.place(x=15, y=277.5)

if len(looping) != 0 and looping[-1]:
    running_label = Label(
        frame_runnung,
        text="실행중: O",
        fg="red",
        borderwidth=1,
        relief="solid",
        font=("맑은 고딕", 10),
        width=20,
        height=10,
    )
    running_label.pack()
else:
    running_label = Label(
        frame_runnung,
        text="실행중: X",
        fg="green",
        borderwidth=1,
        relief="solid",
        font=("맑은 고딕", 10),
        width=20,
        height=10,
    )
    running_label.pack()


frame_error = Frame(frame_settings, width=112.5, height=37.5)
frame_error.pack_propagate(False)
frame_error.place(x=142.5, y=277.5)

error_label = Label(
    frame_error,
    text="오류: X",
    fg="green",
    borderwidth=1,
    relief="solid",
    font=("맑은 고딕", 10),
    width=20,
    height=10,
)
error_label.pack()


# 스킬 프레임
frame_skills = Frame(window, width=270, height=330)
frame_skills.pack_propagate(False)
frame_skills.place(x=270, y=45)


# 스킬
for i in range(1, 7):
    globals()[f"frame_{i}skillK"] = Frame(frame_skills, width=112.5, height=37.5)
    globals()[f"frame_{i}skillK"].pack_propagate(0)
    globals()[f"frame_{i}skillK"].place(x=15, y=15 + (i - 1) * 52.5)

    keys_SV[i - 1].set(HotbarKeys[i - 1])
    globals()[f"entry_key{i}"] = Entry(
        globals()[f"frame_{i}skillK"],
        textvariable=keys_SV[i - 1],
        fg="black",
        borderwidth=1,
        relief="solid",
        justify="center",
        font=("맑은 고딕", 10),
    )
    globals()[f"entry_key{i}"].place(width=80, height=37.5)

    globals()[f"frame_{i}skillN"] = Frame(frame_skills, width=145, height=37.55)
    globals()[f"frame_{i}skillN"].pack_propagate(0)
    globals()[f"frame_{i}skillN"].place(x=110, y=15 + (i - 1) * 52.5)

    nums_DV[i - 1].set(Skill_timeData[i - 1])
    globals()[f"entry_num{i}"] = Entry(
        globals()[f"frame_{i}skillN"],
        textvariable=nums_DV[i - 1],
        fg="black",
        borderwidth=1,
        relief="solid",
        font=("맑은 고딕", 10),
    )
    globals()[f"entry_num{i}"].place(width=145, height=37.5)

    globals()[f"frame_{i}skillC"] = Frame(frame_skills, width=60, height=37.5)
    globals()[f"frame_{i}skillC"].pack_propagate(False)
    globals()[f"frame_{i}skillC"].place(x=195, y=15 + (i - 1) * 52.5)
    globals()[f"frame_{i}skillC"].place_forget()

    clicks_IV[i - 1].set(clicknums[i - 1])
    globals()[f"entry_click{i}"] = Entry(
        globals()[f"frame_{i}skillC"],
        textvariable=clicks_IV[i - 1],
        fg="black",
        borderwidth=1,
        relief="solid",
        font=("맑은 고딕", 10),
    )
    globals()[f"entry_click{i}"].place(width=60, height=37.5)


thread_error = Thread(target=check_error, daemon=True)
thread_error.start()


Label(
    window,
    text="제작자: 데이즈 | 디스코드: pro_days",
    relief=SUNKEN,
    font=("맑은 고딕", 10),
    anchor=tk.W,
    bd=1,
).pack(side=BOTTOM, fill=tk.X)


window.mainloop()
