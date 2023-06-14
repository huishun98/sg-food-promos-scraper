import pytz
import config
import requests
import pygsheets
import pandas as pd

from datetime import datetime
from telethon import sessions
from telethon.sync import TelegramClient
from google.oauth2 import service_account
from telethon.tl.functions.messages import GetHistoryRequest


""" GSheets """
creds = service_account.Credentials.from_service_account_info(
    config.SERVICE_ACCOUNT_INFO, scopes=config.SCOPES
)
gc = pygsheets.authorize(custom_credentials=creds)
gsheet = gc.open_by_key(config.GSHEET_ID)
overview_sheet = gsheet.worksheet_by_title(config.OVERVIEW_SHEETNAME)
data_sheet = gsheet.worksheet_by_title(config.DATA_SHEETNAME)
overview_df = overview_sheet.get_as_df()
columns = [
    "date",
    "channel_username",
    "id",
    "message",
    "_",
    "peer_id",
    "out",
    "mentioned",
    "media_unread",
    "silent",
    "post",
    "from_scheduled",
    "legacy",
    "edit_hide",
    "pinned",
    "noforwards",
    "from_id",
    "fwd_from",
    "via_bot_id",
    "reply_to",
    "media",
    "reply_markup",
    "entities",
    "views",
    "forwards",
    "replies",
    "edit_date",
    "post_author",
    "grouped_id",
    "reactions",
    "restriction_reason",
    "ttl_period",
]

""" Telegram client """
session = sessions.StringSession(config.TELETHON_SESSION)
client = TelegramClient(session, config.API_ID, config.API_HASH)
client.connect()  # Connect to the server
client.get_me()  # Issue a high level command to start receiving message

posts = []
exit_code = 0

# Get the current datetime in UTC
for i, channel_username in enumerate(overview_df["channel"]):
    print(f"[INFO] processing {channel_username}...")

    row = overview_df[overview_df["channel"] == channel_username]
    prev_msg_id = row["latest_msg_id"].iloc[0]
    try:
        prev_msg_id = int(prev_msg_id)
    except Exception:
        print(f"[INFO] {channel_username} does not have a valid prev_msg_id")
        exit_code = 1
        continue

    channel_entity = client.get_entity(channel_username)
    req = GetHistoryRequest(
        peer=channel_entity,
        limit=100,
        offset_date=datetime.now(pytz.utc),
        offset_id=0,
        max_id=0,
        min_id=prev_msg_id + 1,
        add_offset=0,
        hash=0,
    )
    res = client(req)
    msgs = res.messages

    print(f"[INFO] {len(msgs)} new messages scraped, channel={channel_username}")

    if len(msgs) <= 0:
        continue

    for msg in msgs:
        post = msg.to_dict()
        post["channel_username"] = channel_username
        posts.append(post)

    overview_df.loc[i, "latest_msg_id"] = msgs[0].id
    print(
        f"[INFO] prev msg id={prev_msg_id}, new msg id={msgs[0].id}, channel={channel_username}"
    )

if len(posts) <= 0:
    print("[INFO] no new posts")
    exit(exit_code)

print("[INFO] updating google sheets...")
data_sheet.update_row(1, columns)
df = pd.DataFrame(posts)
df = df.applymap(str)
df = df.reindex(columns=columns)
data_sheet.insert_rows(row=1, values=df.values.tolist())
overview_sheet.set_dataframe(overview_df, start="A1")

print("[INFO] updating data.world...")
headers = {
    "Authorization": f"Bearer {config.DATA_WORLD_API_TOKEN}",
    "Content-type": "application/x-www-form-urlencoded",
}
url = "https://api.data.world/v0/datasets/huishun98/sg-food-promos/sync"
response = requests.post(url, headers=headers)
print(f"[INFO] status={response.status_code}, response={response.json()['message']}")
if response.status_code != 200:
    exit_code = 1

exit(exit_code)
