import io
import os
import typing
from math import ceil

import urllib3
from PIL import Image, ImageFont, ImageDraw

import SETTINGS

urllib3.disable_warnings()


class Module:
    def __init__(self):
        self.path = os.path.dirname(os.path.abspath(__file__))  # I like to use abs path, makes me feel safe
        self.http = urllib3.PoolManager()

    def get_blend_color(self, rarity):
        mapping = {
            'frozen': (148, 223, 255),
            'lava': (234, 141, 35),
            'legendary': (167, 78, 66),
            'dark': (251, 34, 223),
            'starwars': (231, 196, 19),
            'marvel': (197, 51, 52),
            'mythic': (255, 253, 112),
            'dc': (84, 117, 199),
            'icon': (54, 183, 183),
            'shadow': (113, 113, 113),
            'epic': (177, 91, 226),
            'rare': (73, 172, 242),
            'uncommon': (96, 170, 58),
            'common': (190, 190, 190),
            'slurp': (41, 150, 182),
            'backup': (255, 255, 255)
        }
        return mapping.get(rarity.lower()) or mapping.get('backup')

    def open_and_fail(self, base: str, backup: typing.Optional[str] = None):
        try:
            layer = Image.open(base)
        except Exception:
            layer = Image.open(backup)
        return layer

    def paste(self, card, layer_path, layer_backup, **kwargs):
        layer = self.open_and_fail(base=self.path + layer_path, backup=self.path + layer_backup)
        if kwargs.get('double'):
            return card.paste(layer, layer)
        return card.paste(layer)

    def _handle_rarity_text(self, card, Draw, blend_color, display_rarity, display_category) -> None:
        BurbankBigCondensed = ImageFont.truetype(f"assets/Fonts/BurbankBigCondensed-Black.otf", 30)
        textWidth = BurbankBigCondensed.getsize(f"{display_rarity.capitalize()} {display_category.capitalize()}")[0]

        Middle = int((card.width - textWidth) / 2)
        Draw.text((Middle, 370), f"{display_rarity.capitalize()} {display_category.capitalize()}", blend_color,
                  font=BurbankBigCondensed)

    def _handle_display_text(self, card, Draw, set) -> None:  # STATIC METHOD GO BRR
        if not set:
            return None

        set_text = set.get('text')
        if set_text:
            font_size = 56
            while ImageFont.truetype(f"assets/Fonts/BurbankBigCondensed-Black.otf", font_size).getsize(set_text)[
                0] > 265:
                font_size -= 1

            BurbankBigCondensed = ImageFont.truetype(f"assets/Fonts/BurbankBigCondensed-Black.otf", font_size)
            text_width = BurbankBigCondensed.getsize(set_text)[0]
            change = 56 - font_size

            middle = int((card.width - text_width) / 2)
            top = 470 + change / 2
            Draw.text((middle, top), set_text, (255, 255, 255), font=BurbankBigCondensed)

    def generate_card(self, data) -> Image:
        """The actual card generation part for each card.

        I would have usually made this async (bc aiohttp), but we're not going to because of the thread pool executor.

        There are many ways to clean this up, but tbh I don't care enough to."""
        card = Image.new("RGB", (300, 545))
        Draw = ImageDraw.Draw(card)

        name = data.get('name') or 'Placeholder'
        rarity = data['rarity']['value'].lower() or 'common'
        display_rarity = data["rarity"]["displayValue"] or 'common'
        category = data['type']['value'] or 'Placeholder'
        display_category = data["type"]["displayValue"] or 'Placeholder'
        blend_color = self.get_blend_color(rarity)

        inside = f'/assets/Images/card_inside_{rarity.lower()}.png'
        inside_backup = '/assets/Images/card_inside_common.png'
        self.paste(  # We use the paste func just so it's a bit neater.
            card=card, layer_path=inside,
            layer_backup=inside_backup
        )

        images = [data['images'][entry] for entry in data['images']]
        icon = images[0] if images else "https://i.imgur.com/JPuoAAu.png"

        icon = Image.open(io.BytesIO(self.http.urlopen("GET", icon).data)).resize((512, 512), Image.ANTIALIAS)

        if category in ('outfit', 'emote'):
            ratio = max(285 / icon.width, 365 / icon.height)
        elif category == "wrap":
            ratio = max(230 / icon.width, 310 / icon.height)
        else:
            ratio = max(310 / icon.width, 390 / icon.height)

        icon = icon.resize((int(icon.width * ratio), int(icon.height * ratio)), Image.ANTIALIAS).convert("RGBA")
        middle = int((card.width - icon.width) / 2)  # Get the middle of card and icon

        card.paste(icon, (middle, 0 if category in ('outfit', 'emote') else 15), icon)

        faceplate = f'/assets/Images/card_faceplate_{rarity.lower()}.png'  # Open the card faceplate
        faceplate_backup = '/assets/Images/card_faceplate_common.png'
        self.paste(
            card=card, layer_path=faceplate,
            layer_backup=faceplate_backup, double=True
        )

        if SETTINGS.raritytext:
            self._handle_rarity_text(card, Draw, blend_color, display_rarity, display_category)

        font_size = 56
        while ImageFont.truetype(f"assets/Fonts/BurbankBigCondensed-Black.otf", font_size).getsize(name)[0] > 265:
            font_size -= 1

        BurbankBigCondensed = ImageFont.truetype(f"assets/Fonts/BurbankBigCondensed-Black.otf", font_size)
        textWidth = BurbankBigCondensed.getsize(name)[0]
        change = 56 - font_size

        middle = int((card.width - textWidth) / 2)
        top = 415 + change / 2

        Draw.text((middle, top), name, (255, 255, 255), font=BurbankBigCondensed)

        if SETTINGS.displayset:
            self._handle_display_text(card, Draw, data.get('set'))

        if SETTINGS.watermark != "":  # No custom func for this, 2 lines is ok.
            font = ImageFont.truetype(f"assets/Fonts/BurbankBigCondensed-Black.otf", SETTINGS.watermarksize)
            Draw.text((5, 5), SETTINGS.watermark, (255, 255, 255), font=font)

        return card

    def generate_image_array(self, images, imagesPerRow, half: bool = False):

        frame_width = 1920
        padding = 3
        images_per_row = imagesPerRow

        img_width, img_height = images[0].size
        sf = (frame_width - (images_per_row - 1) * padding) / (images_per_row * img_width)
        scaled_img_width = ceil(img_width * sf)
        scaled_img_height = ceil(img_height * sf)

        number_of_rows = ceil(len(images) / images_per_row)
        frame_height = ceil(sf * img_height * number_of_rows)

        new_im = Image.new('RGBA', (frame_width, frame_height), (0, 0, 0))

        i, j = 0, 0
        for num, im in enumerate(images):
            if num % images_per_row == 0:
                i = 0
            im.thumbnail((scaled_img_width, scaled_img_height))
            y_cord = (j // images_per_row) * scaled_img_height
            new_im.paste(im, (i, y_cord))
            i = (i + scaled_img_width) + padding
            j += 1
        if half:
            width, height = new_im.size
            width = round(width / 2)
            height = round(height / 2)
            new_im = new_im.resize((width, height), Image.ANTIALIAS)

        return new_im
