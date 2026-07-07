"""Tests voor de live Slack-leestools (list_slack_channels, read_slack_channel, search_slack).

Alles gemockt op slack_sdk.WebClient — geen enkele test raakt de echte Slack API.
"""

from unittest.mock import MagicMock, patch

import tools


def _channels_resp(channels, next_cursor=""):
    return {"channels": channels, "response_metadata": {"next_cursor": next_cursor}}


def test_list_slack_channels_no_token(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    result = tools.list_slack_channels()
    assert "error" in result


def test_list_slack_channels_success(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    fake_client = MagicMock()
    fake_client.conversations_list.return_value = _channels_resp([
        {"id": "C1", "name": "nn-ks-it", "is_private": False, "is_member": True, "topic": {"value": "KS/IT"}},
    ])
    with patch("slack_sdk.WebClient", return_value=fake_client):
        result = tools.list_slack_channels()
    assert result["total"] == 1
    assert result["channels"][0]["id"] == "C1"
    assert result["truncated"] is False


def test_resolve_slack_channel_id_accepts_raw_id():
    fake_client = MagicMock()
    resolved = tools._resolve_slack_channel_id(fake_client, "C0BAFJ1GDF1")
    assert resolved == "C0BAFJ1GDF1"
    fake_client.conversations_list.assert_not_called()


def test_resolve_slack_channel_id_resolves_name_with_hash():
    fake_client = MagicMock()
    fake_client.conversations_list.return_value = _channels_resp([
        {"id": "C1", "name": "nn-ks-it"},
    ])
    resolved = tools._resolve_slack_channel_id(fake_client, "#nn-ks-it")
    assert resolved == "C1"


def test_read_slack_channel_channel_not_found(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    fake_client = MagicMock()
    fake_client.conversations_list.return_value = _channels_resp([])
    with patch("slack_sdk.WebClient", return_value=fake_client):
        result = tools.read_slack_channel("#does-not-exist")
    assert "error" in result


def test_read_slack_channel_success_with_thread_replies(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    fake_client = MagicMock()
    fake_client.conversations_history.return_value = {
        "messages": [
            {"ts": "100.0", "user": "U1", "text": "Voorstel status?", "thread_ts": "100.0", "reply_count": 1},
        ],
        "response_metadata": {"next_cursor": ""},
    }
    fake_client.conversations_replies.return_value = {
        "messages": [
            {"ts": "100.0", "user": "U1", "text": "Voorstel status?"},
            {"ts": "101.0", "user": "U2", "text": "Nog geen antwoord."},
        ]
    }
    with patch("slack_sdk.WebClient", return_value=fake_client):
        result = tools.read_slack_channel("C0BAFJ1GDF1", since_days=10)
    assert result["total"] == 1
    assert result["messages"][0]["replies"][0]["text"] == "Nog geen antwoord."
    assert result["truncated"] is False


def test_search_slack_filters_on_keyword(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    fake_client = MagicMock()
    fake_client.conversations_history.return_value = {
        "messages": [
            {"ts": "1.0", "user": "U1", "text": "Jane en Louis zijn de sponsors"},
            {"ts": "2.0", "user": "U2", "text": "Iets totaal anders"},
        ],
        "response_metadata": {"next_cursor": ""},
    }
    with patch("slack_sdk.WebClient", return_value=fake_client):
        result = tools.search_slack("jane", channel="C0BAFJ1GDF1")
    assert len(result["results"]) == 1
    assert "Jane" in result["results"][0]["text"]


def test_search_slack_no_query_terms_returns_no_results(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    fake_client = MagicMock()
    fake_client.conversations_history.return_value = {
        "messages": [{"ts": "1.0", "user": "U1", "text": "iets"}],
        "response_metadata": {"next_cursor": ""},
    }
    with patch("slack_sdk.WebClient", return_value=fake_client):
        result = tools.search_slack("   ", channel="C0BAFJ1GDF1")
    assert result["results"] == []


def test_dispatch_wires_new_slack_tools(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    fake_client = MagicMock()
    fake_client.conversations_list.return_value = _channels_resp([])
    with patch("slack_sdk.WebClient", return_value=fake_client):
        raw = tools.dispatch("list_slack_channels", {})
    import json
    parsed = json.loads(raw)
    assert parsed["total"] == 0
