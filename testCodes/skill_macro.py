from genericpath import isfile
import pyautogui
import keyboard
import tkinter
import os
import time
import threading


global skill_axis
global hotbar_keys
global ongoing
global keyboard_f9
keyboard_f9 = True


def store_key():
    for i in range(6):
        key = keyboard.read_key()
        time.sleep(0.5)
        HotbarKeys[i] = key
        keys.config(text=", ".join(HotbarKeys))

    text = "".join(HotbarKeys) + "\n"
    with open("C:\Temp\PD_SkillMacro.txt", "w") as f:
        f.write(text)
    f.close()


def macro():
    pos1, pos2, pos3, pos4, pos5, pos6 = None, None, None, None, None, None
    while keyboard_f9:
        if not pos1:
            pos1 = pyautogui.locateOnScreen(
                "image\\1.png", confidence=0.99)
            if pos1:
                keyboard.press(HotbarKeys[0])
                pos1 = tuple(pos1)
                print(1)
        elif pyautogui.locateOnScreen(
                "image\\1.png", confidence=0.99, region=pos1):
            keyboard.press(HotbarKeys[0])
            print(1)

        if not pos2:
            pos2 = pyautogui.locateOnScreen(
                "image\\2.png", confidence=0.99)
            if pos2:
                keyboard.press(HotbarKeys[1])
                pos2 = tuple(pos2)
                print(2)
        elif pyautogui.locateOnScreen(
                "image\\2.png", confidence=0.99, region=pos2):
            keyboard.press(HotbarKeys[1])
            print(2)

        if not pos3:
            pos3 = pyautogui.locateOnScreen(
                "image\\3.png", confidence=0.99)
            if pos3:
                keyboard.press(HotbarKeys[2])
                pos3 = tuple(pos3)
                print(3)
        elif pyautogui.locateOnScreen(
                "image\\3.png", confidence=0.99, region=pos3):
            keyboard.press(HotbarKeys[2])
            print(3)

        if not pos4:
            pos4 = pyautogui.locateOnScreen(
                "image\\4.png", confidence=0.99)
            if pos4:
                keyboard.press(HotbarKeys[3])
                pos4 = tuple(pos4)
                print(4)
        elif pyautogui.locateOnScreen(
                "image\\4.png", confidence=0.99, region=pos4):
            keyboard.press(HotbarKeys[3])
            print(4)

        if not pos5:
            pos5 = pyautogui.locateOnScreen(
                "image\\5.png", confidence=0.99)
            if pos5:
                keyboard.press(HotbarKeys[4])
                pos5 = tuple(pos5)
                print(5)
        elif pyautogui.locateOnScreen(
                "image\\5.png", confidence=0.99, region=pos5):
            keyboard.press(HotbarKeys[4])
            print(5)

        if not pos6:
            pos6 = pyautogui.locateOnScreen(
                "image\\6.png", confidence=0.99)
            if pos6:
                keyboard.press(HotbarKeys[5])
                pos6 = tuple(pos6)
                print(6)
        elif pyautogui.locateOnScreen(
                "image\\6.png", confidence=0.99, region=pos6):
            keyboard.press(HotbarKeys[5])
            print(6)

        print(pos1, pos2, pos3, pos4, pos5, pos6)
        time.sleep(0.05)


def keyboard_is_pressed():
    global keyboard_f9
    keyboard_f9 = True
    while keyboard_f9:
        if keyboard.is_pressed("f9"):
            keyboard_f9 = False
            return None
        time.sleep(0.05)


global HotbarKeys

skill_axis = [[], [], [], [], [], []]

if os.path.isfile("C:\Temp\PD_SkillMacro.txt"):
    with open("C:\Temp\PD_SkillMacro.txt", "r") as f:
        SkillData = f.readline()
        HotbarKeys = list(SkillData.replace("\n", ""))
else:
    HotbarKeys = [2, 3, 4, 5, 6, 7]


window = tkinter.Tk()


# window.title("ProDays Skill Macro")
window.title("Macro")
window.geometry("500x300+100+100")
# 500x300
window.resizable(False, False)


outtext = tkinter.Label(
    window, text="이미지 번호에 맞는 키보드 키를 입력하세요. \n입력이 완료되면 esc키를 입력하세요.")
outtext.pack()


global keys
keys = tkinter.Label(
    window, text=", ".join(HotbarKeys))
keys.pack()


btn1 = tkinter.Button(window, text="키보드 입력", width=10,
                      command=lambda: threading.Thread(target=store_key).start())
btn1.place(x=10, y=250)


def start_macro():
    t1 = threading.Thread(target=macro)
    t1.start()
    t2 = threading.Thread(target=keyboard_is_pressed)
    t2.start()


btn2 = tkinter.Button(window, text="실행", width=10,
                      command=lambda: start_macro())
btn2.place(x=380, y=250)

window.mainloop()
