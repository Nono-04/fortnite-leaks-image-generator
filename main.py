import io
import json
import math
import sys
import time
import traceback

import urllib3
from PIL import Image

import SETTINGS
import module

urllib3.disable_warnings()
http = urllib3.PoolManager()

lang = SETTINGS.lang
if not lang:
    lang = "en"


def get_response():
    with open('cache/benbot.json', 'r') as fnapi_file:
        benbot_cache = json.load(fnapi_file)
    benbot_new = json.loads(
        http.request("get", f'https://benbotfn.tk/api/v1/newCosmetics?lang={lang}').data.decode('utf-8'))
    if benbot_cache != benbot_new:
        with open('cache/benbot.json', 'w') as file:
            json.dump(benbot_new, file, indent=3)
        print("BenBot was updated")
        if "error" in benbot_new:
            print(f"BenBot Error: " + benbot_new['error'])
            return
        if not benbot_new['items']:
            print("BenBot Error: Items Null")
            return
        globaldata = {
            "status": 200,
            "data": {
                "items": [{
                    "id": cosmetic["id"],
                    "name": cosmetic["name"],
                    "description": cosmetic["description"],
                    "type": {
                        "value": cosmetic["shortDescription"],
                        "displayValue": cosmetic["shortDescription"],
                        "backendValue": cosmetic["backendType"]
                    },
                    "set": {
                        "text": cosmetic["setText"],
                    },
                    "rarity": {
                        "value": cosmetic["backendRarity"].split("::")[1],
                        "displayValue": str(cosmetic["backendRarity"]).replace("Athena", "").lower(),
                        "backendValue": cosmetic["backendRarity"]
                    },
                    "images": {
                        "smallIcon": cosmetic["icons"]["icon"],
                        "featured": cosmetic["icons"]["featured"],
                        "icon": cosmetic["icons"]["icon"],
                        "other": cosmetic["icons"]["icon"],
                    }
                } for cosmetic in benbot_new["items"]]
            }
        }
        with open('cache/benbot.json', 'w') as file:
            json.dump(benbot_new, file, indent=3)
        return globaldata

    with open('cache/fortniteapi.json', 'r') as fnapi_file:
        fnapi_cache = json.load(fnapi_file)
    fnapi_new = json.loads(
        http.request("get", f'https://fortnite-api.com/v2/cosmetics/br/new?language={lang}').data.decode('utf-8'))

    if fnapi_cache != fnapi_new:
        print("Fortnite-API.com was updated")
        with open('cache/fortniteapi.json', 'w') as file:
            json.dump(fnapi_new, file, indent=3)
        globaldata = {
            "status": 200,
            "data": {
                "items": [
                ]
            }
        }
        if "error" in fnapi_new:
            print("Fortnite API Error: " + fnapi_new['error'])
            return
        for cosmetic in fnapi_new["data"]["items"]:
            cosmetic["rarity"] = {
                "value": cosmetic["rarity"]["value"],
                "displayValue": cosmetic["rarity"]["displayValue"],
                "backendValue": cosmetic["rarity"]["backendValue"]
            }
            globaldata["data"]["items"].append(cosmetic)

        return fnapi_new

    return None


def check():
    new = get_response()
    if new:
        start = time.time()
        print(f"\n----------------------------\n"
              f"!!!    Leaks detected    !!!"
              f"\n----------------------------\n"
              f"\nDownloading now the Images")
        try:
            if SETTINGS.downloadcards is False:
                files = [module.GenerateCard(i) for i in new["data"]["items"] if
                         SETTINGS.typeconfig[i["type"]["backendValue"]] is True]
            else:
                files = []
                for i in new["data"]["items"]:
                    if SETTINGS.typeconfig[i['type']['backendValue']] is True:
                        img = module.GenerateCard(i)
                        img.save(f"output/{i['name']}.png", optimized=True)
                        files.append(f"output/{i['name']}")
        except:
            traceback.print_exc()
            print("ERROR WITH DOWNLOADING FILES.\n"
                  "THERE WAS ADDED A NEW ITEM TYPE VALUE."
                  "\nMAKE NOW A NEW IMAGE WITH ALL TYPES")
            files = [module.GenerateCard(i) for i in new["data"]["items"]]
        if not files:
            raise FileNotFoundError("No Images")
        print(f"Image Download completed\nThe download taked: {round(time.time()-start, 2)} seconds ({round(round(time.time()-start, 2) / len(new['data']['items']), 4)}sec/{len(new['data']['items'])} card)\n\nParse now all Images to one Image")
        result = Image.new("RGBA", (
            round(math.sqrt(len(files)) + 0.45) * 305 - 5, round(math.sqrt(len(files))) * 550 - 5))
        if SETTINGS.backgroundurl != "":
            result.paste(Image.open(io.BytesIO(http.urlopen("GET", SETTINGS.backgroundurl).data)).resize((int(round(math.sqrt(len(files)) + 0.45) * 305 - 5),int(round(math.sqrt(len(files)) + 0.45) * 550 - 5)),Image.ANTIALIAS))
        x = -305
        y = 0
        count = 0
        for img in files:
            try:
                img.thumbnail((305, 550), Image.ANTIALIAS)
                w, h = img.size
                if count >= round(math.sqrt(len(files)) + 0.45):
                    y += 550
                    x = -305
                    count = 0
                x += 305
                count += 1
                result.paste(img, (x, y, x + w, y + h))
            except:
                continue
        result.save(f"leaks.png", optimized=True)
        print(f"Finished.\n\nGenerating Image in {round(time.time() - start, 2)}sec")
        result.show()
        time.sleep(30)
        sys.exit()


if __name__ == "__main__":
    count = 0
    while True:
        count = 1 + count
        print(f"Checking for Leaks ({count})")
        check()
        time.sleep(SETTINGS.interval)
