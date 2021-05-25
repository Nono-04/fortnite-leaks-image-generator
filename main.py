import concurrent.futures
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
import asyncio

urllib3.disable_warnings()
http = urllib3.PoolManager()
Module = module.Module()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=15)
loop = asyncio.get_event_loop()

lang = SETTINGS.lang or 'en'


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
            return print(f"BenBot Error: " + benbot_new['error'])
        if not benbot_new['items']:
            return print("BenBot Error: Items Null")

        globaldata = {  # Benbot API sucks. ONG
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


def run(i):
    return Module.generate_card(i)


async def check():
    """Check for any new cosmetics and download them."""
    new = get_response()
    if not new:
        return None

    start = time.time()
    print(f"\n----------------------------\n"
          f"!!!    Leaks detected    !!!"
          f"\n----------------------------\n"
          f"\nDownloading the Images now.")

    try:  # We're streaming all the cards, I'm not downloading them thats dumb
        futures = [loop.run_in_executor(executor, run, i) for i in new["data"]["items"] if
                   SETTINGS.typeconfig[i["type"]["backendValue"]]]
    except Exception:
        traceback.print_exc()
        print("ERROR WITH DOWNLOADING FILES.\n"
              "THERE WAS ADDED A NEW ITEM TYPE VALUE."
              "\nMAKE NOW A NEW IMAGE WITH ALL TYPES")
        futures = [loop.run_in_executor(executor, run, i) for i in new["data"]["items"]]  # Build futures although we failed

    if not futures:  # Catch the error if there's no new data.
        raise FileNotFoundError("No Images")

    print(f"Image Download completed\n"
          f"The download taked: {round(time.time() - start, 2)} seconds ({round(round(time.time() - start, 2) / len(new['data']['items']), 4)}sec/{len(new['data']['items'])} card)"
          f"\n\nGathering Images Now.")

    try:
        files = await asyncio.gather(*futures)
    except Exception as E:
        traceback.print_exc()
        return print("RAN INTO AN ISSUE GATHERING FILES, ABORTING NOW.")

    print("DONE GATHERING, MERGING IMAGES NOW.")

    result = Image.new("RGBA", (
        round(math.sqrt(len(files)) + 0.45) * 305 - 5, round(math.sqrt(len(files))) * 550 - 5))
    if SETTINGS.backgroundurl != "":
        result.paste(Image.open(io.BytesIO(http.urlopen("GET", SETTINGS.backgroundurl).data)).resize((int(
            round(math.sqrt(len(files)) + 0.45) * 305 - 5), int(round(math.sqrt(len(files)) + 0.45) * 550 - 5)),
            Image.ANTIALIAS))

    # Your old way of merging images gave me aids, in a nice way.
    # I honestly didnt know how it worked, and I kinda like that so I'm leaving it.
    # I added my image merged in module.py if you want to switch to it later.

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


async def main():
    if __name__ == "__main__":
        count = 0
        while True:
            count += 1
            print(f"Checking for Leaks ({count})")

            await check()

            await asyncio.sleep(SETTINGS.interval)

loop.run_until_complete(main())
