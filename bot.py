import logging
import os
from io import BytesIO

import telegram
from telegram.ext import Updater, MessageHandler, Filters
from dotenv import load_dotenv, find_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv(find_dotenv())


font = ImageFont.truetype("SourceSansPro-Regular.ttf", 48)


def apply(name, photo):
    outfile = BytesIO()
    with Image.open('orig.png') as base:
        result = base.convert('RGBA')
        icon = Image.open(BytesIO(photo)).convert('RGBA')
        icon = icon.transform(base.size, Image.PERSPECTIVE, [1/0.39, 0, -430, 0.01807, 1/0.49, -365, 0, 0, 1])
        result.alpha_composite(icon)

        draw = ImageDraw.Draw(result)
        nw, nh = draw.textsize(name, font=font)
        draw.rectangle([(420 - nw / 2, 100 - nh / 2), (420 + nw / 2, 100 + nh / 2)], fill=(190, 190, 190, 255))
        draw.text((420 - nw / 2, 100 - nh / 2), name, font=font, fill=(0, 0, 0, 255))

        result.save(outfile, 'PNG')
    return outfile.getvalue()


def process(update: telegram.Update, context):
    target = update.effective_user
    if update.effective_message is not None and update.effective_message.forward_from is not None:
        target = update.effective_message.forward_from
    name = target.full_name
    photos = target.get_profile_photos(limit=1).photos
    if len(photos) == 0:
        error = "Can't find profile picture for {}".format(name)
        context.bot.send_message(chat_id=update.effective_chat.id, text=error)
        return
    photo_all_sizes = target.get_profile_photos(limit=1).photos[0]
    photo_best_size = max(photo_all_sizes, key=lambda x: x.width)
    photo_file = photo_best_size.get_file()
    photo = photo_file.download_as_bytearray()
    result = apply(name, photo)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=BytesIO(result))
    log_message = 'Handled request for "{}"'.format(name)
    if target is not update.effective_user:
        log_message += ' on behalf of "{}"'.format(update.effective_user.full_name)
    logger.info(log_message)


if __name__ == "__main__":
    # Set these variable to the appropriate values
    TOKEN = os.environ.get('TG_BOT_TOKEN')
    NAME = "head-receiver-bot"

    # Port is given by Heroku
    PORT = os.environ.get('PORT')

    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set up the Updater
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher
    # Add handlers
    dp.add_handler(MessageHandler(Filters.all, process))

    # Start the webhook
    if PORT is None:
        updater.start_polling()
    else:
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=TOKEN)
        updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(NAME, TOKEN))
    updater.idle()
