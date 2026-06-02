import pytest
from app.services.discord_bot_publisher import DiscordBotPublisher


def test_split_content_short():
    pub = DiscordBotPublisher()
    content = "Short message"
    chunks = pub._split_content(content, max_len=1900)
    assert len(chunks) == 1
    assert chunks[0] == content


def test_split_content_long():
    pub = DiscordBotPublisher()
    content = "A" * 3000
    chunks = pub._split_content(content, max_len=1900)
    assert len(chunks) == 2
    assert all(len(c) <= 1900 for c in chunks)


def test_split_content_multiple():
    pub = DiscordBotPublisher()
    content = "Line 1\n" * 500
    chunks = pub._split_content(content, max_len=500)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)
