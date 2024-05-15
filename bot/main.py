import logging
import os

import requests
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from torch import seed

from bot.setting import API_TOKEN
from bot.text import *

URL = "http://localhost:8004"

CHOOSING, SELECT_MODEL, SEND_PHOTO, CHECK_TASK = range(4)
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

reply_keyboard = [["Check photo", "Help", "Done"]]
select_model_reply_keyboard = [["EfficientNet", "ResNet"]]


class BotHandler:
    __users_files = {}

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start command from handler"""
        name = update.message.from_user.first_name
        if not name:
            name = "User"

        self.__users_files[update.message.from_user.id] = {}
        self.__users_files[update.message.from_user.id]["full_name"] = (
            update.message.from_user.full_name
        )
        self.__users_files[update.message.from_user.id]["images"] = []

        await update.message.reply_text(
            get_start_text(name),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CHOOSING

    async def done_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """End command from handler"""
        user_data = context.user_data
        if "choice" in user_data:
            del user_data["choice"]

        if update.message.from_user.id in self.__users_files.keys():
            for filename in self.__users_files[update.message.from_user.id]["images"]:
                cur_file = os.path.join(filename)
                os.remove(cur_file)
            del self.__users_files[update.message.from_user.id]

        await update.message.reply_text(
            end_text,
            reply_markup=ReplyKeyboardRemove(),
        )

        user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Help command from handler"""
        await update.message.reply_text(help_text)

    async def check_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Initiating the process of performing image verification for spoofing detection."""

        await update.message.reply_text(
            "Select model",
            reply_markup=ReplyKeyboardMarkup(
                select_model_reply_keyboard, one_time_keyboard=True
            ),
        )
        return SELECT_MODEL

    async def select_model(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        selected_model = update.message.text
        if selected_model not in select_model_reply_keyboard[0]:
            await update.message.reply_text("Choose network from keyboard")
            return SELECT_MODEL

        match selected_model:
            case "EfficientNet":
                selected_model = "efficient_net"
            case "ResNet":
                selected_model = "resnet"

        self.__users_files[user_id]["selected_model"] = selected_model
        await update.message.reply_text(create_paths)
        return SEND_PHOTO

    async def send_picture(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = update.message.from_user.id
        if user_id not in self.__users_files:
            self.__users_files[user_id] = {"files": []}

        if update.message.photo:
            user_file = await context.bot.get_file(update.message.photo[-1].file_id)

        elif update.message.document:
            user_file = await context.bot.get_file(update.message.document.file_id)
            extension = os.path.splitext(user_file.file_path)[1]
            if extension.lower() not in ALLOWED_EXTENSIONS:
                await update.message.reply_text(
                    "Please send the file in JPEG or PNG format."
                )
                return CHOOSING

        else:
            await update.message.reply_text(
                "Please send an image or file in JPEG or PNG format."
            )
            return CHOOSING

        file_name = os.path.basename(user_file.file_path)

        await user_file.download_to_drive(custom_path=file_name)
        self.__users_files[user_id]["images"].append(file_name)

        await context.bot.sendMessage(
            chat_id=update.message.chat_id, text="I get it successful! Wait pls!"
        )

        url = f"{URL}/check_photo_bot"
        with open(file_name, "rb") as file:
            file = {
                "image": (file_name, file.read(), f"image/jpeg"),
            }
            data = {
                "bot_token": API_TOKEN,
                "user_id": update.message.chat_id,
                "reply_message": update.message.message_id,
                "selected_model": self.__users_files[user_id]["selected_model"],
            }
            response = requests.post(url, data=data, files=file)
        os.remove(file_name)

        if response.status_code == 200:
            task_id = response.json()["task_id"]
            await update.message.reply_text(
                f"The image processing task received the ID: {task_id}",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True
                ),
            )
        else:
            await update.message.reply_text(
                "There was an error sending the image to the server.\nTry sending the image later"
            )

        return CHOOSING


def main() -> None:
    app = Application.builder().token(API_TOKEN).build()
    Bot = BotHandler()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", Bot.start_command)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex("^(Check photo|/check)$"), Bot.check_command
                ),
                MessageHandler(filters.Regex("^(Help|/help)$"), Bot.help_command),
            ],
            SELECT_MODEL: [
                MessageHandler(filters.TEXT, Bot.select_model),
            ],
            SEND_PHOTO: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, Bot.send_picture)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^(Done|/done)$"), Bot.done_command)],
    )
    app.add_handler(conversation_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
