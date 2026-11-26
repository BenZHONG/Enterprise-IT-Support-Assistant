"""Rule-based replies for Stage 1.

Later stages replace the body of get_reply() with an AI-powered flow.
The function name and signature stay the same, so callers do not change.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    """One support topic: a name, trigger keywords, and a prepared reply."""

    name: str
    keywords: tuple[str, ...]
    reply: str


# Order matters: the first topic with a matching keyword wins.
TOPICS: tuple[Topic, ...] = (
    Topic(
        name="wifi",
        keywords=("wifi", "wi-fi", "wireless"),
        reply=(
            "For Wi-Fi problems: 1) Turn Wi-Fi off and on again. "
            "2) Forget the company network and reconnect. "
            "3) Restart your laptop. "
            "If it still fails, tell me and I can help raise a ticket later."
        ),
    ),
    Topic(
        name="vpn",
        keywords=("vpn",),
        reply=(
            "For VPN problems: 1) Check you have normal internet access first. "
            "2) Close and reopen the VPN app. "
            "3) Restart your laptop and try again."
        ),
    ),
    Topic(
        name="password",
        keywords=("password", "locked out", "login", "log in"),
        reply=(
            "For password problems, use the self-service reset page. "
            "IT Support will never ask for your password. "
            "Never share your password, not even in this chat."
        ),
    ),
    Topic(
        name="microsoft365",
        keywords=(
            "outlook",
            "teams",
            "microsoft 365",
            "office 365",
            "m365",
            "onedrive",
        ),
        reply=(
            "For Microsoft 365 problems: 1) Sign out and sign in again. "
            "2) Check the Microsoft 365 service status page. "
            "3) Restart the app."
        ),
    ),
    Topic(
        name="hardware",
        keywords=("laptop", "battery", "keyboard", "screen", "mouse", "hardware"),
        reply=(
            "For hardware problems: 1) Restart the device. "
            "2) Check cables and power. "
            "3) Note any error message. "
            "Hardware faults usually need a ticket for a technician."
        ),
    ),
    Topic(
        name="outage",
        keywords=("outage", "network down", "internet down"),
        reply=(
            "I cannot check live outages yet (that arrives in Stage 7). "
            "Please ask a colleague nearby if they have the same problem."
        ),
    ),
)

FALLBACK_REPLY = (
    "I am not sure about that yet. I can help with Wi-Fi, VPN, passwords, "
    "Microsoft 365, hardware, and outages. Type 'quit' to leave."
)


def normalise(message: str) -> str:
    """Lowercase the text and collapse repeated spaces."""
    return " ".join(message.lower().split())


def find_topic(message: str) -> Topic | None:
    """Return the first topic whose keyword appears in the message."""
    text = normalise(message)
    for topic in TOPICS:
        if any(keyword in text for keyword in topic.keywords):
            return topic
    return None


def get_reply(message: str) -> str:
    """Return the assistant's reply to one employee message."""
    topic = find_topic(message)
    return topic.reply if topic else FALLBACK_REPLY
