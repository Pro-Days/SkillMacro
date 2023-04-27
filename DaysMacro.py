# 모듈

from requests import get
from threading import Thread
from time import sleep
import os.path
from tkinter import Tk, Label, DoubleVar, IntVar, StringVar, Entry, ttk, Button, Frame, font
from keyboard import read_key, is_pressed, read_hotkey
from pyautogui import press, click
from webbrowser import open_new


# 함수 선언

def version_check():
    try:
        response = get(
            "https://api.github.com/repos/pro-days/skillmacro/releases/latest")
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
    if "nums_DV" in globals():

        # 프리셋 바꿀 때 에러

        Skill_timeData = [str(i.get()) for i in nums_DV]
        Skill_timeData.append(str(reduce_skill_cooltime.get()))
        # Skill_timeData, delaytime = [str(i.get()) for i in nums_DV].append(
        #     str(reduce_skill_cooltime.get())), delay.get()
        # print(Skill_timeData)

        HotbarKeys = [str(i.get()) for i in keys_SV]
        clicknums = [str(i.get()) for i in clicks_IV]
    else:
        Skill_timeData = [str(i) for i in Skill_timeData]
        Skill_timeData.append(str(reduce_skill_cooltime.get()))
        # print(Skill_timeData)
        clicknums = [str(i) for i in clicknums]
    if preset == "1":
        with open(f"C:\\ProDays\\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(" ".join(HotbarKeys) + "\n" + " ".join(Skill_timeData) + "\n" +
                    str(start_key) + "\n" + str(delay.get()) + "\n" + " ".join(clicknums))
    else:
        with open(f"C:\\ProDays\\PD_SkillMacro{preset}.txt", "w") as f:
            f.write(" ".join(Skill_timeData) + "\n" + " ".join(clicknums))


def store_startkey():
    global start_key, startkey_stored
    startkey_stored = False
    start_key = read_key()
    with open(f"C:\\ProDays\\PD_SkillMacro1.txt", "r") as f:
        text = f.readlines()
    text[2] = str(start_key) + "\n"

    with open(f"C:\\ProDays\\PD_SkillMacro1.txt", "w") as f:
        f.writelines(text)
    sleep(0.2)
    startkey_stored = True
    thread_key = Thread(target=keyboard_clicked, daemon=True)
    thread_key.start()
    startkey_button.config(text=start_key)


def loop(ln, n):
    sleep(nums_DV[ln].get() * (100-reduce_skill_cooltime.get())/100 + delay.get() / 200)
    press_key[n].append(ln)


def afk(n):
    sec = 0
    while looping[n]:
        key = read_hotkey()
        key = set(key.split("+"))
        for i in range(6):
            if keys_SV[i].get() in key:
                key.remove(keys_SV[i].get())

        if key:
            sec = 0
            # print("sec = 0")
        else:
            sec += 1
            # print("sec += 1")
        if sec == 100:
            # print("sec == 5")
            looping[-1] = False
            running_label.config(text="실행중: X", fg="green")
            return
        sleep(1)


def macro(n):

    # click{n} == 0: thread.start()

    press_key.append([])
    m = combobox_mode.get() == "모드 2"

    for i in range(6):
        press_key[n].append(i)

    Thread(target=afk, args=[n]).start()

    while looping[n]:
        # print(press_key)
        if press_key[n]:
            # press_key[n].sort()
            for idx in range(6):
                if press_key[n][0] == idx:
                    press(keys_SV[idx].get())
                    if m:  # 클릭 딜레이 따로 만들기
                        if clicks_IV[idx].get() != 0:
                            for i in range(clicks_IV[idx].get()):
                                sleep(delay.get()/100)
                                if looping[n]:
                                    click()
                                    if i == 0:
                                        Thread(target=loop, args=[idx, n]).start()
                                else:
                                    break
                        else:
                            Thread(target=loop, args=[idx, n]).start()
                            sleep(delay.get()/100)
                    else:
                        Thread(target=loop, args=[idx, n]).start()
                        sleep(delay.get()/100)
            del press_key[n][0]
        else:
            sleep(delay.get()/100)


def dataload(event):
    global HotbarKeys, Skill_timeData, start_key, delaytime, clicknums
    preset = combobox_preset.get() if "combobox_preset" in globals() else "1"

    if os.path.isfile(f"C:\\ProDays\\PD_SkillMacro{preset}.txt"):
        try:
            with open(f"C:\\ProDays\\PD_SkillMacro{preset}.txt", "r") as f:
                text = f.readlines()
                if preset == "1":
                    if len(text) == 5:
                        SkillData = text[0].replace("\n", "")
                        HotbarKeys = SkillData.split(" ")
                        if len(HotbarKeys) != 6:
                            HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                        Skill_timeData = text[1].replace("\n", "")
                        Skill_timeData = Skill_timeData.split(" ")

                        if len(Skill_timeData) != 7:
                            Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                        start_key = text[2].replace("\n", "")
                        delaytime = int(text[3].replace("\n", ""))
                        clicknums = text[4].replace("\n", "").split(" ")
                        if len(clicknums) != 6:
                            clicknums = [1, 1, 1, 1, 1, 1]

                        if "nums_DV" in globals():
                            for i, j in enumerate(nums_DV):
                                j.set(float(Skill_timeData[i]))

                            reduce_skill_cooltime.set(int(Skill_timeData[6]))
                            delay.set(delaytime)

                            for i, j in enumerate(clicks_IV):
                                j.set(int(clicknums[i]))
                    else:
                        clicknums = [1, 1, 1, 1, 1, 1]
                        HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                        start_key = "f9"
                        delaytime = 15
                        store_all(preset)
                else:
                    if len(text) == 2:
                        Skill_timeData = text[0].replace("\n", "")
                        Skill_timeData = Skill_timeData.split(" ")

                        if len(Skill_timeData) != 7:
                            Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]

                        clicknums = text[1].replace("\n", "").split(" ")
                        if len(clicknums) != 6:
                            clicknums = [1, 1, 1, 1, 1, 1]

                        if "nums_DV" in globals():

                            for i, j in enumerate(nums_DV):
                                j.set(float(Skill_timeData[i]))

                            reduce_skill_cooltime.set(int(Skill_timeData[6]))

                            for i, j in enumerate(clicks_IV):
                                j.set(int(clicknums[i]))
                    else:
                        Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                        clicknums = [1, 1, 1, 1, 1, 1]
                        store_all(preset)
        except:
            if preset == "1":
                if not os.path.exists("C:\\ProDays"):
                    os.makedirs("C:\\ProDays")
                HotbarKeys = ["2", "3", "4", "5", "6", "7"]
                Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                clicknums = [1, 1, 1, 1, 1, 1]
                start_key = "f9"
                delaytime = 15
                if "nums_DV" in globals():
                    for i, j in enumerate(nums_DV):
                        j.set(float(Skill_timeData[i]))

                    reduce_skill_cooltime.set(Skill_timeData[6])
                    delay.set(delaytime)

                    for i, j in enumerate(clicks_IV):
                        j.set(int(clicknums[i]))
            else:
                Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
                clicknums = [1, 1, 1, 1, 1, 1]

                for i, j in enumerate(nums_DV):
                    j.set(float(Skill_timeData[i]))

                reduce_skill_cooltime.set(Skill_timeData[6])

                for i, j in enumerate(clicks_IV):
                    j.set(int(clicknums[i]))
            store_all(preset)

    else:
        if preset == "1":
            if not os.path.exists("C:\\ProDays"):
                os.makedirs("C:\\ProDays")
            HotbarKeys = ["2", "3", "4", "5", "6", "7"]
            Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
            clicknums = [1, 1, 1, 1, 1, 1]
            start_key = "f9"
            delaytime = 15
            if "nums_DV" in globals():
                for i, j in enumerate(nums_DV):
                    j.set(float(Skill_timeData[i]))

                reduce_skill_cooltime.set(Skill_timeData[6])
                delay.set(delaytime)

                for i, j in enumerate(clicks_IV):
                    j.set(int(clicknums[i]))
        else:
            Skill_timeData = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
            clicknums = [1, 1, 1, 1, 1, 1]

            for i, j in enumerate(nums_DV):
                j.set(float(Skill_timeData[i]))

            reduce_skill_cooltime.set(Skill_timeData[6])

            for i, j in enumerate(clicks_IV):
                j.set(int(clicknums[i]))
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
                error = True
                error_label.config(text="오류: X", fg="green")
            else:
                error_label.config(text="오류: O", fg="red")

        sleep(0.5)


def modechange(event):
    if combobox_mode.get() == "모드 1":
        for i in range(1, 7):
            globals()[f"frame_{i}skillK"].config(width=112.5, height=37.5)
            globals()[f"entry_key{i}"].place(width=80, height=37.5)

            globals()[f"frame_{i}skillN"].config(width=145, height=37.5)
            globals()[f"frame_{i}skillN"].place(x=110, y=15 + (i-1) * 52.5)
            globals()[f"entry_num{i}"].place(width=145, height=37.5)

            globals()[f"frame_{i}skillC"].place_forget()
    else:
        for i in range(1, 7):
            globals()[f"frame_{i}skillK"].config(width=60)
            globals()[f"entry_key{i}"].place(width=60, height=37.5)

            globals()[f"frame_{i}skillN"].config(width=90)
            globals()[f"frame_{i}skillN"].place(x=90, y=15 + (i-1) * 52.5)
            globals()[f"entry_num{i}"].place(width=90, height=37.5)

            globals()[f"frame_{i}skillC"].place(x=195, y=15 + (i-1) * 52.5)


# 변수 선언, main

version = "v8.0"
looping = []
startkey_stored = True
press_key = []
error = False


dataload(None)


thread_key = Thread(target=keyboard_clicked, daemon=True)
thread_key.start()


window = Tk()


window.title("데이즈매크로 " + version)
window.geometry("540x375+100+100")
window.resizable(False, False)


# 리스트 속에 배치
nums_DV = [DoubleVar() for i in range(6)]
# num1, num2, num3, num4, num5, num6 = [DoubleVar() for i in range(6)]
keys_SV = [StringVar() for i in range(6)]
# keys1, keys2, keys3, keys4, keys5, keys6 = [StringVar() for i in range(6)]
clicks_IV = [IntVar() for i in range(6)]
# click1, click2, click3, click4, click5, click6 = [IntVar() for i in range(6)]


path = os.path.join(os.path.dirname(__file__), 'icon.ico')
if os.path.isfile(path):
    window.iconbitmap(path)


# 업데이트 체크
frame_update = Frame(window, width=270, height=45)
frame_update.pack_propagate(False)
frame_update.place(x=0, y=0)

update_label = Label(frame_update, text="업데이트 확인중...", fg="gray", borderwidth=1.5, relief="solid",
                     font=("맑은 고딕", 12, "bold"), width=20, height=10)
update_label.pack()

thread_version = Thread(target=version_check, daemon=True)
thread_version.start()


# 설명 링크
frame_descr = Frame(window, width=270, height=45)
frame_descr.pack_propagate(False)
frame_descr.place(x=270, y=0)

descr_label = Label(frame_descr, text="설명 확인하기", fg="blue", borderwidth=1.5, relief="solid",
                    font=("맑은 고딕", 12, "bold"), width=20, height=10)
descr_label.pack()
descr_label.bind(
    "<Button-1>", lambda event: open_new("https://github.com/Pro-Days/SkillMacro#readme"))


# 설정 프레임
frame_settings = Frame(window, width=270, height=330)
frame_settings.pack_propagate(False)
frame_settings.place(x=0, y=45)


# 딜레이
frame_delayT = Frame(frame_settings, width=112.5, height=37.5)
frame_delayT.pack_propagate(False)
frame_delayT.place(x=15, y=15)

Label(frame_delayT, text="딜레이", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_delayN = Frame(frame_settings, width=112.5, height=37.5)
frame_delayN.pack_propagate(False)
frame_delayN.place(x=142.5, y=15)

delay = IntVar()
delay.set(delaytime)
Entry(frame_delayN, textvariable=delay, fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10)).place(width=112.5, height=37.5)


# 쿨타임감소
frame_rscT = Frame(frame_settings, width=112.5, height=37.5)
frame_rscT.pack_propagate(False)
frame_rscT.place(x=15, y=67.5)

Label(frame_rscT, text="쿨타임감소", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_rscN = Frame(frame_settings, width=112.5, height=37.5)
frame_rscN.pack_propagate(False)
frame_rscN.place(x=142.5, y=67.5)

reduce_skill_cooltime = IntVar()
reduce_skill_cooltime.set(int(Skill_timeData[6]))
Entry(frame_rscN, textvariable=reduce_skill_cooltime, fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10)).place(width=112.5, height=37.5)


# 시작키설정
frame_startkeyT = Frame(frame_settings, width=112.5, height=37.5)
frame_startkeyT.pack_propagate(False)
frame_startkeyT.place(x=15, y=120)

Label(frame_startkeyT, text="시작키설정", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_startkeyK = Frame(frame_settings, width=112.5, height=37.5)
frame_startkeyK.pack_propagate(False)
frame_startkeyK.place(x=142.5, y=120)

startkey_button = Button(frame_startkeyK, text=start_key, width=10, borderwidth=1, relief="solid",
                         font=("맑은 고딕", 10), bg="white", anchor="center", command=store_startkey)
startkey_button.pack()


# 프리셋
frame_presetT = Frame(frame_settings, width=112.5, height=37.5)
frame_presetT.pack_propagate(False)
frame_presetT.place(x=15, y=172.5)

Label(frame_presetT, text="프리셋", fg="black", borderwidth=1, relief="solid",
      font=("맑은 고딕", 10), width=20, height=10).pack()


frame_presetN = Frame(frame_settings, width=112.5, height=37.5)
frame_presetN.pack_propagate(False)
frame_presetN.place(x=142.5, y=172.5)

combobox_preset = ttk.Combobox(
    frame_presetN, font=("맑은 고딕", 10),
    values=["1", "2", "3", "4", "5"],
    state="readonly", justify="center")
combobox_preset.current(0)
combobox_preset.place(width=112.5, height=37.5)
combobox_preset.bind("<<ComboboxSelected>>", dataload)


# 저장 & 모드
frame_store = Frame(frame_settings, width=112.5, height=37.5)
frame_store.pack_propagate(False)
frame_store.place(x=15, y=225)

Button(frame_store, text="저장", width=10, borderwidth=1, relief="solid", font=("맑은 고딕", 10),
       bg="white", anchor="center", command=lambda: store_all(combobox_preset.get())).pack()


frame_mode = Frame(frame_settings, width=112.5, height=37.5)
frame_mode.pack_propagate(False)
frame_mode.place(x=142.5, y=225)

combobox_mode = ttk.Combobox(
    frame_mode, font=("맑은 고딕", 10),
    values=["모드 1", "모드 2"],
    state="readonly", justify="center")
combobox_mode.current(0)
combobox_mode.place(width=112.5, height=37.5)
combobox_mode.bind("<<ComboboxSelected>>", modechange)


# 정보표시
frame_runnung = Frame(frame_settings, width=112.5, height=37.5)
frame_runnung.pack_propagate(False)
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
frame_error.pack_propagate(False)
frame_error.place(x=142.5, y=277.5)

error_label = Label(frame_error, text="오류: X", fg="green", borderwidth=1, relief="solid",
                    font=("맑은 고딕", 10), width=20, height=10)
error_label.pack()


# 스킬 프레임
frame_skills = Frame(window, width=270, height=330)
frame_skills.pack_propagate(False)
frame_skills.place(x=270, y=45)


# 스킬
for i in range(1, 7):
    globals()[f"frame_{i}skillK"] = Frame(
        frame_skills, width=112.5, height=37.5)
    globals()[f"frame_{i}skillK"].pack_propagate(0)
    globals()[f"frame_{i}skillK"].place(x=15, y=15 + (i-1) * 52.5)

    keys_SV[i - 1].set(HotbarKeys[i-1])
    globals()[f"entry_key{i}"] = Entry(
        globals()[f"frame_{i}skillK"],
        textvariable=keys_SV[i - 1],
        fg="black", borderwidth=1, relief="solid", justify="center", font=("맑은 고딕", 10))
    globals()[f"entry_key{i}"].place(width=80, height=37.5)

    globals()[f"frame_{i}skillN"] = Frame(
        frame_skills, width=145, height=37.55)
    globals()[f"frame_{i}skillN"].pack_propagate(0)
    globals()[f"frame_{i}skillN"].place(x=110, y=15 + (i-1) * 52.5)

    nums_DV[i - 1].set(Skill_timeData[i-1])
    globals()[f"entry_num{i}"] = Entry(
        globals()[f"frame_{i}skillN"],
        textvariable=nums_DV[i - 1],
        fg="black", borderwidth=1, relief="solid", font=("맑은 고딕", 10))
    globals()[f"entry_num{i}"].place(width=145, height=37.5)

    globals()[f"frame_{i}skillC"] = Frame(
        frame_skills, width=60, height=37.5)
    globals()[f"frame_{i}skillC"].pack_propagate(False)
    globals()[f"frame_{i}skillC"].place(x=195, y=15 + (i-1) * 52.5)
    globals()[f"frame_{i}skillC"].place_forget()

    clicks_IV[i - 1].set(clicknums[i-1])
    globals()[f"entry_click{i}"] = Entry(
        globals()[f"frame_{i}skillC"],
        textvariable=clicks_IV[i - 1],
        fg="black", borderwidth=1, relief="solid", font=("맑은 고딕", 10))
    globals()[f"entry_click{i}"].place(width=60, height=37.5)


thread_error = Thread(target=check_error, daemon=True)
thread_error.start()


window.mainloop()
