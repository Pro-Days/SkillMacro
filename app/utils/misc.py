def convert7to5(shared_data, num):
    for x, y in enumerate(shared_data.selectedSkillList):  # x: 0~5, y: 0~7
        if y == num:
            return x


def isKeyUsing(shared_data, key):
    """
    가상 키보드 생성 중 키가 사용중인지 확인
    """

    key = key.replace("\n", "_")
    usingKey = []

    if shared_data.activeStartKeySlot == 1:
        usingKey.append(shared_data.inputStartKey)
    else:
        usingKey.append("F9")

    for i in shared_data.skillKeys:
        usingKey.append(i)

    for i in shared_data.linkSkillList:
        if i["keyType"] == 1:
            usingKey.append(i["key"])

    # if self.settingType == 3:
    #     usingKey.append(self.ButtonLinkKey1.text())

    # print(usingKey, key)

    return key in usingKey
