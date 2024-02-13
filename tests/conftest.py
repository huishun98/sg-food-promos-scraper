import pandas as pd
import pytest
from unittest.mock import MagicMock, Mock


@pytest.fixture
def mock_telegram_client(monkeypatch):
    mock_client = MagicMock()
    mock_connect = MagicMock()
    mock_client.connect = mock_connect
    monkeypatch.setattr("main.TelegramClient", MagicMock(return_value=mock_client))
    return mock_client


@pytest.fixture
def mock_google_sheets():
    data_sheet_mock = Mock()
    overview_sheet_mock = Mock()
    return data_sheet_mock, overview_sheet_mock


@pytest.fixture
def mock_overview_df():
    # Create a mock DataFrame with necessary columns
    return pd.DataFrame(
        {"channel": ["channel1", "channel2"], "latest_msg_id": [123, 456]}
    )
