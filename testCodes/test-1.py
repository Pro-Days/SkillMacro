import json

preset = int(input())

with open(f"C:\\ProDays\\DaysMacro.json", "r") as f:
    json_object = json.load(f)

    HotbarKeys = json_object['HotbarKeys']
    Skill_timeData = json_object['Skill_timeData'][str(preset)]
    Skill_timeData.append(json_object['reduce_skill_cooltime'][str(preset)])
    start_key = json_object['start_key']
    delaytime = json_object['delaytime']
    clicknums = json_object['clicknums'][str(preset)]

print("Hotbarkeys: " + str(HotbarKeys))
print("Skill_timeData: " + str(Skill_timeData))
print("start_key: " + str(start_key))
print("delaytime: " + str(delaytime))
print("clicknums: " + str(clicknums))


json_object['HotbarKeys'] = ["2", "3", "4", "5", "6", "7"]
json_object['Skill_timeData'][str(preset)] = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
json_object['start_key'] = "f10"
json_object['delaytime'] = 20
json_object['clicknums'][str(preset)] = [1, 2, 3, 4, 5, 6]


with open('C:\\ProDays\\DaysMacro.json', 'w') as f:
    json.dump(json_object, f, indent=2)
