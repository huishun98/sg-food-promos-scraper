import json, base64
from os import getenv
from dotenv import load_dotenv

load_dotenv()

""" Telegram client config """
# For more info on how to obtain these values, refer to
# https://shallowdepth.online/posts/2021/12/end-to-end-tests-for-telegram-bots/
# https://blog.1a23.com/2020/03/06/how-to-write-integration-tests-for-a-telegram-bot/
API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")

# with TelegramClient(sessions.StringSession(), API_ID, API_HASH) as client:
#     print("Session string:", client.session.save())
TELETHON_SESSION = getenv("TELETHON_SESSION")

""" GSheets config """
# Create the Google Sheet manually. Set all values as plain text format.
# Remember to share the Google Sheet with SERVICE_ACCOUNT_INFO_CLIENT_EMAIL
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
GSHEET_ID = getenv("GSHEET_ID")  # can be found in the gsheet's url
OVERVIEW_SHEETNAME = "Sheet1"  # defaults to Sheet1.
DATA_SHEETNAME = "Sheet2"  # defaults to Sheet2.
COLS = [
    "date",
    "channel_username",
    "scraped_at",
    "id",
    "message",
    "_",
    "peer_id",
    # "out",
    # "mentioned",
    # "media_unread",
    "silent",
    # "post",
    # "from_scheduled",
    # "legacy",
    "edit_hide",
    "pinned",
    # "noforwards",
    # "from_id",
    "fwd_from",
    # "via_bot_id",
    "reply_to",
    "media",
    # "reply_markup",
    "entities",
    "views",
    "forwards",
    "replies",
    "edit_date",
    # "post_author",
    # "grouped_id",
    "reactions",
    # "restriction_reason",
    # "ttl_period",
]

# To use Google Sheets API,
# create a google cloud project: https://developers.google.com/workspace/guides/create-project
# create service account credentials: https://developers.google.com/workspace/guides/create-credentials#service-account
SERVICE_ACCOUNT_INFO_B64 = getenv("SERVICE_ACCOUNT_INFO_B64")
SERVICE_ACCOUNT_INFO = base64.b64decode(SERVICE_ACCOUNT_INFO_B64).decode("utf-8")
SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_INFO)

"""data.world config"""
DATA_WORLD_API_TOKEN = getenv("DATA_WORLD_API_TOKEN")
