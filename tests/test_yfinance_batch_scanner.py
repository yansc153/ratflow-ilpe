import asyncio

from app.config import settings
from app.data_sources.yfinance_scanner import YFinanceScanner


def test_scanner_loads_file_universe_and_rotates_batches(tmp_path, monkeypatch):
    universe = tmp_path / "universe.txt"
    state = tmp_path / "scan_cursor.json"
    universe.write_text("aapl, msft\n# comment\nNVDA\nAAPL\nTSLA\n")

    monkeypatch.setattr(settings, "ticker_universe_file", str(universe))
    monkeypatch.setattr(settings, "scan_cursor_state_file", str(state))
    monkeypatch.setattr(settings, "scan_batch_size", 2)

    scanner = YFinanceScanner()

    first = scanner._next_ticker_batch(scanner._load_ticker_universe(), settings.scan_batch_size)
    second = scanner._next_ticker_batch(scanner._load_ticker_universe(), settings.scan_batch_size)
    third = scanner._next_ticker_batch(scanner._load_ticker_universe(), settings.scan_batch_size)

    assert first == ["AAPL", "MSFT"]
    assert second == ["NVDA", "TSLA"]
    assert third == ["AAPL", "MSFT"]


def test_fetch_scans_only_current_batch(tmp_path, monkeypatch):
    universe = tmp_path / "universe.txt"
    state = tmp_path / "scan_cursor.json"
    universe.write_text("AAPL\nMSFT\nNVDA\nTSLA\n")

    monkeypatch.setattr(settings, "ticker_universe_file", str(universe))
    monkeypatch.setattr(settings, "scan_cursor_state_file", str(state))
    monkeypatch.setattr(settings, "scan_batch_size", 2)

    scanned = []

    def fake_scan(ticker):
        scanned.append(ticker)
        return []

    scanner = YFinanceScanner()
    monkeypatch.setattr(scanner, "_scan_ticker", fake_scan)

    asyncio.run(scanner.fetch_unusual_options())

    assert scanned == ["AAPL", "MSFT"]
