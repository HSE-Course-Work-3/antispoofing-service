def get_start_text(name: str) -> str:
    return (
        f"Hello, {name}!\nI'm AI AntiSpoofing bot! I can check your photo for spoofing!"
    )


no_pics = f"You didnt load any pictures!"

create_paths = f"Upload an image which you want to check for spoofing"

help_text = "For checking pictures for spoofing do this step by step:\n \
    1) Use command /check and after that send picture. (English language, pls!!!)\n \
    2) Copy the task id to be sent by the bot then write the /status command and paste the copied id\n \
    If you want to finish, send me /done command."

end_text = f"Goodbye!)"
