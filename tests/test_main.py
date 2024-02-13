import pytest
from unittest.mock import Mock, patch
from main import *
import config


class MockWorksheet:
    def __init__(self, rows):
        self.rows = rows

    def get_all_records(self):
        return self.rows

    def delete_rows(self, index):
        # Minus 2 because pygsheets index starts from 1, and there's a header row
        del self.rows[index - 2]

    def update_cells(self, cell_range, data):
        pass


def test_remove_old_rows():
    # Create a mock worksheet with some rows
    current_date = datetime.now(pytz.utc)
    date_12_months_ago = current_date - timedelta(days=365)
    old_date = (date_12_months_ago - timedelta(days=1)).strftime(date_format)
    recent_date = (current_date - timedelta(days=1)).strftime(date_format)
    rows = [{"date": old_date}, {"date": recent_date}]
    sorted_rows = sorted(
        rows, key=lambda x: datetime.strptime(x["date"], date_format), reverse=True
    )
    worksheet = MockWorksheet(sorted_rows)

    # Call the function
    remove_old_rows(worksheet)

    # Assert that the old row is removed
    assert len(worksheet.rows) == 1
    assert worksheet.rows[0]["date"] == recent_date

    # Test with no rows to delete
    worksheet = MockWorksheet([])
    remove_old_rows(worksheet)  # Should not raise an error

    # Test with all rows older than 12 months
    very_old_date = (date_12_months_ago - timedelta(days=1)).strftime(date_format)
    rows = [{"date": very_old_date}]
    worksheet = MockWorksheet(rows)
    remove_old_rows(worksheet)
    assert len(worksheet.rows) == 0


class TestGetChannelMessages:
    class MockMessage:
        def __init__(self, message_id, content):
            self.id = message_id
            self.content = content

        def to_dict(self):
            return {"id": self.id, "content": self.content}

    class MockClientResponse:
        def __init__(self, messages):
            self.messages = messages

    def test_get_channel_messages(self, mock_telegram_client):
        channel_username = "test_channel"
        prev_msg_id = 123456789

        messages = [self.MockMessage(2, "Message 2"), self.MockMessage(1, "Message 1")]
        mock_telegram_client.return_value = self.MockClientResponse(messages)

        posts, latest_msg_id = get_channel_messages(
            mock_telegram_client, channel_username, prev_msg_id
        )

        assert isinstance(posts, list)
        assert len(posts) == 2
        assert isinstance(latest_msg_id, int)
        assert latest_msg_id == 2

        mock_telegram_client.get_entity.assert_called_once_with(channel_username)
        mock_telegram_client.assert_called_once()

    def test_no_new_messages(self, mock_telegram_client):
        channel_username = "test_channel"
        prev_msg_id = 123456789

        posts, latest_msg_id = get_channel_messages(
            mock_telegram_client, channel_username, prev_msg_id
        )

        assert isinstance(posts, list)
        assert len(posts) == 0
        assert isinstance(latest_msg_id, int)
        assert latest_msg_id == prev_msg_id

        mock_telegram_client.get_entity.assert_called_once_with(channel_username)
        mock_telegram_client.assert_called_once()


def test_get_telegram_client(mock_telegram_client):
    client = get_telegram_client()
    assert client == mock_telegram_client
    mock_telegram_client.connect.assert_called_once()


def test_update_google_sheets_no_posts(
    capfd: pytest.CaptureFixture[str], mock_google_sheets: tuple[Mock, Mock]
):
    data_sheet_mock, overview_sheet_mock = mock_google_sheets
    update_google_sheets(data_sheet_mock, overview_sheet_mock, [], [], None)
    captured = capfd.readouterr()
    assert "[INFO] no new posts\n" in captured.out


def test_update_google_sheets_with_posts(
    monkeypatch: pytest.MonkeyPatch, mock_google_sheets: tuple[Mock, Mock]
):
    # Unpack the mocked objects
    data_sheet_mock, overview_sheet_mock = mock_google_sheets

    # Mock DataFrame and related functions
    mock_df = Mock()
    mock_df.values.tolist.return_value = [[1, "title1"], [2, "title2"]]  # Example data
    mock_df.applymap.return_value = mock_df  # Return self
    mock_df.reindex.return_value = mock_df  # Return self

    # Define a function to return the mock DataFrame
    def mock_dataframe(*args, **kwargs):
        return mock_df

    monkeypatch.setattr("main.pd.DataFrame", mock_dataframe)

    # Mock other necessary functions
    data_sheet_mock.update_row.return_value = None
    data_sheet_mock.append_table.return_value = None
    overview_sheet_mock.set_dataframe.return_value = None
    data_sheet_mock.sort_range.return_value = None

    # Call the function with posts
    update_google_sheets(
        data_sheet_mock, overview_sheet_mock, ["id", "title"], [1, "title1"], mock_df
    )

    # Check if the necessary methods were called with correct arguments
    data_sheet_mock.update_row.assert_called_once_with(1, ["id", "title"])
    data_sheet_mock.append_table.assert_called_once_with(
        [[1, "title1"], [2, "title2"]],
        start="A1",
        end=None,
        dimension="ROWS",
        overwrite=False,
    )
    overview_sheet_mock.set_dataframe.assert_called_once_with(mock_df, start="A1")
    data_sheet_mock.sort_range.assert_called_once_with(
        "A2", "AZ301454", sortorder="DESCENDING"
    )


@patch("main.requests.post")
def test_update_data_world(mock_requests_post, capfd: pytest.CaptureFixture[str]):
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Sync completed successfully"}

    # Set up mock post method
    mock_requests_post.return_value = mock_response

    # Call the function
    status_code = update_data_world()

    # Check if the post method was called with the correct arguments
    mock_requests_post.assert_called_once_with(
        "https://api.data.world/v0/datasets/huishun98/sg-food-promos/sync",
        headers={
            "Authorization": f"Bearer {config.DATA_WORLD_API_TOKEN}",
            "Content-type": "application/x-www-form-urlencoded",
        },
    )

    # Check if the returned status code matches the mock response
    assert status_code == 200

    # Check if the print statement was called with the correct message
    captured = capfd.readouterr()
    assert "[INFO] status=200, response=Sync completed successfully" in captured.out
