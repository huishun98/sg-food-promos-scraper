import pytz
import config
import requests
import pygsheets
import pandas as pd

from datetime import datetime, timedelta
from telethon import sessions
from telethon.sync import TelegramClient
from google.oauth2 import service_account
from telethon.tl.functions.messages import GetHistoryRequest

date_format = "%Y-%m-%d %H:%M:%S%z"


def get_google_sheets_client():
    creds = service_account.Credentials.from_service_account_info(
        config.SERVICE_ACCOUNT_INFO, scopes=config.SCOPES
    )
    return pygsheets.authorize(custom_credentials=creds)


def get_telegram_client():
    session = sessions.StringSession(config.TELETHON_SESSION)
    client = TelegramClient(session, config.API_ID, config.API_HASH)
    client.connect()
    return client


def get_channel_messages(client, channel_username, prev_msg_id):
    posts = []
    channel_entity = client.get_entity(channel_username)
    req = GetHistoryRequest(
        peer=channel_entity,
        limit=100,
        offset_date=datetime.now(pytz.utc),
        offset_id=0,
        max_id=0,
        min_id=prev_msg_id,
        add_offset=0,
        hash=0,
    )
    res = client(req)
    msgs = res.messages
    print(f"[INFO] {len(msgs)} new messages scraped, channel={channel_username}")

    if len(msgs) <= 0:
        return [], prev_msg_id

    for msg in msgs:
        post = msg.to_dict()
        post["channel_username"] = channel_username
        post["scraped_at"] = datetime.now(pytz.utc)
        posts.append(post)

    return posts, msgs[0].id


def update_google_sheets(data_sheet, overview_sheet, columns, posts, overview_df):
    if len(posts) <= 0:
        print("[INFO] no new posts")
        return

    data_sheet.update_row(1, columns)
    df = pd.DataFrame(posts)
    df = df.applymap(str)
    df = df.reindex(columns=columns)
    vals = df.values.tolist()

    try:
        data_sheet.append_table(
            vals, start="A1", end=None, dimension="ROWS", overwrite=False
        )
    except pygsheets.exceptions.RequestError as e:
        print(f"[ERROR] {e.message}")  # or use e.response.text to get the full response
        return e.response.status_code

    overview_sheet.set_dataframe(overview_df, start="A1")
    data_sheet.sort_range("A2", "AZ301454", sortorder="DESCENDING")


def remove_old_rows(worksheet, days=365):
    # Get the current date and date 12 months ago
    current_date = datetime.now(pytz.utc)
    date_12_months_ago = current_date - timedelta(days=days)

    # Get all values from the worksheet
    rows = worksheet.get_all_records()

    # Iterate through rows from the bottom and remove rows where the date is more than 12 months before now
    for row in reversed(rows):
        row_date = datetime.strptime(row["date"], date_format)
        if row_date > date_12_months_ago:
            break
        # Adding 2 because pygsheets index starts from 1, and there's a header row
        worksheet.delete_rows(rows.index(row) + 2)


def update_data_world():
    headers = {
        "Authorization": f"Bearer {config.DATA_WORLD_API_TOKEN}",
        "Content-type": "application/x-www-form-urlencoded",
    }
    url = "https://api.data.world/v0/datasets/huishun98/sg-food-promos/sync"
    response = requests.post(url, headers=headers)
    print(
        f"[INFO] status={response.status_code}, response={response.json()['message']}"
    )
    return response.status_code


if __name__ == "__main__":
    gsheets_client = get_google_sheets_client()
    gsheets_wb = gsheets_client.open_by_key(config.GSHEET_ID)
    overview_sheet = gsheets_wb.worksheet_by_title(config.OVERVIEW_SHEETNAME)
    data_sheet = gsheets_wb.worksheet_by_title(config.DATA_SHEETNAME)

    overview_df = overview_sheet.get_as_df()
    overview_df["latest_msg_id"] = overview_df["latest_msg_id"].astype(int)

    telegram_client = get_telegram_client()

    posts = []
    for i, channel_username in enumerate(overview_df["channel"]):
        row = overview_df[overview_df["channel"] == channel_username]
        prev_msg_id = row["latest_msg_id"].iloc[0]
        channel_posts, last_msg_id = get_channel_messages(
            telegram_client, channel_username, prev_msg_id
        )
        posts = posts + channel_posts
        overview_df.loc[i, "latest_msg_id"] = last_msg_id

    if len(posts) <= 0:
        print("[INFO] nothing to update, exiting...")
        exit()

    print("[INFO] updating google sheets...")
    status_code = update_google_sheets(
        data_sheet, overview_sheet, config.COLS, posts, overview_df
    )
    if status_code == 400:
        remove_old_rows(data_sheet)
        update_google_sheets(
            data_sheet, overview_sheet, config.COLS, posts, overview_df
        )

    print("[INFO] updating data.world...")
    status_code = update_data_world()

    exit(status_code != 200)
