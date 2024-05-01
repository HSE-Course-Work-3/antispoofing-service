import os
import logging
import requests

from bot.text import *
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, filters, Application, CommandHandler, MessageHandler, ConversationHandler

URL = 'http://localhost:8004'
API_TOKEN = '6735438031:AAH8-wZ7EdomMXPbOv-vEOIMflXBmcmdi4Y'

CHOOSING, SEND_PHOTO, CHECK_TASK = range(3)
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

reply_keyboard = [["Check photo", "Get task status", "Help", "Done"]]


class BotHandler:
    __users_files = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command from handler"""
        name = update.message.from_user.first_name
        if not name:
            name = 'User'

        self.__users_files[update.message.from_user.id] = {}
        self.__users_files[update.message.from_user.id]['full_name'] = update.message.from_user.full_name
        self.__users_files[update.message.from_user.id]['images'] = []

        await update.message.reply_text(get_start_text(name),
                                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return CHOOSING

    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """End command from handler"""
        user_data = context.user_data
        if "choice" in user_data:
            del user_data["choice"]

        if update.message.from_user.id in self.__users_files.keys():
            for filename in self.__users_files[update.message.from_user.id]['images']:
                cur_file = os.path.join(filename)
                os.remove(cur_file)
            del self.__users_files[update.message.from_user.id]

        await update.message.reply_text(end_text, reply_markup=ReplyKeyboardRemove(), )

        user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Help command from handler"""
        await update.message.reply_text(help_text)

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Initiating the process of performing image verification for spoofing detection."""
        await update.message.reply_text(create_paths)
        return SEND_PHOTO

    async def send_picture(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.message.from_user.id
        if user_id not in self.__users_files:
            self.__users_files[user_id] = {'files': []}

        if update.message.photo:
            user_file = await context.bot.get_file(update.message.photo[-1].file_id)

        elif update.message.document:
            user_file = await context.bot.get_file(update.message.document.file_id)
            extension = os.path.splitext(user_file.file_path)[1]
            if extension.lower() not in ALLOWED_EXTENSIONS:
                await update.message.reply_text("Please send the file in JPEG or PNG format.")
                return CHOOSING

        else:
            await update.message.reply_text("Please send an image or file in JPEG or PNG format.")
            return CHOOSING

        file_name = os.path.basename(user_file.file_path)

        await user_file.download_to_drive(custom_path=file_name)
        self.__users_files[user_id]['images'].append(file_name)

        await context.bot.sendMessage(
            chat_id=update.message.chat_id,
            text="I get it successful! Wait pls!"
        )

        url = f"{URL}/check_photo"
        with open(file_name, 'rb') as file:
            files = {'image': (file_name, file.read(), f'image/jpeg')}
            response = requests.post(url, files=files)

        if response.status_code == 200:
            task_id = response.json()['task_id']
            await update.message.reply_text(f"The image processing task received the ID: {task_id}")
        else:
            await update.message.reply_text(
                "There was an error sending the image to the server.\nTry sending the image later")

        return CHOOSING

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Enter the ID of the task you want to know the status of")
        return CHECK_TASK

    async def get_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        task_id = update.message.text
        url = f"{URL}/check_photo/{task_id}"
        response = requests.get(url)

        if response.status_code == 200:
            result = response.json()
            task_status = result["task_status"]
            task_result = result["task_result"]
            await update.message.reply_text(
                f"Task Id {task_id}:\nStatus: {task_status}\nResults: {task_result}")
        else:
            await update.message.reply_text("An error occurred while obtaining task status.")

        return CHOOSING


def main() -> None:
    app = Application.builder().token(API_TOKEN).build()
    Bot = BotHandler()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', Bot.start_command)],
        states={
            CHOOSING: [MessageHandler(filters.Regex("^(Check photo|/check)$"),
                                      Bot.check_command),
                       MessageHandler(filters.Regex("^(Get task status|/status)$"),
                                      Bot.status_command),
                       MessageHandler(filters.Regex("^(Help|/help)$"),
                                      Bot.help_command)],
            SEND_PHOTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, Bot.send_picture)],
            CHECK_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, Bot.get_status)],
        },
        fallbacks=[MessageHandler(filters.Regex("^(Done|/done)$"), Bot.done_command)]
    )
    app.add_handler(conversation_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)
