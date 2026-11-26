import pytest

from assistant_app.responder import FALLBACK_REPLY, find_topic, get_reply


@pytest.mark.parametrize(
    ("message", "expected_topic"),
    [
        ("My Wi-Fi keeps dropping", "wifi"),
        ("wireless is slow", "wifi"),
        ("VPN will not connect", "vpn"),
        ("I forgot my password", "password"),
        ("I am locked out", "password"),
        ("Outlook will not open", "microsoft365"),
        ("Teams crashed", "microsoft365"),
        ("my laptop battery is dead", "hardware"),
        ("is there a network outage in Sydney", "outage"),
    ],
)
def test_message_maps_to_expected_topic(message, expected_topic):
    topic = find_topic(message)
    assert topic is not None
    assert topic.name == expected_topic


def test_unknown_message_gets_fallback():
    assert find_topic("tell me a joke") is None
    assert get_reply("tell me a joke") == FALLBACK_REPLY


def test_matching_ignores_case_and_extra_spaces():
    topic = find_topic("  WI-FI   is   DOWN ")
    assert topic is not None
    assert topic.name == "wifi"


def test_password_reply_warns_not_to_share_password():
    assert "never share your password" in get_reply("reset my password").lower()
