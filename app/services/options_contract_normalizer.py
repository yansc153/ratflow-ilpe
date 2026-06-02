from app.models import OptionAlert, InvestigationCase
from app.logging_config import logger


class OptionsContractNormalizer:
    @staticmethod
    def normalize(alert: OptionAlert) -> dict:
        oi = alert.open_interest or 0
        volume = alert.volume or 0
        ratio = round(volume / oi, 2) if oi > 0 else None

        mid_price = None
        if alert.bid is not None and alert.ask is not None:
            mid_price = round((alert.bid + alert.ask) / 2, 2)

        strike = alert.strike
        underlying = alert.underlying_price or 0
        otm_pct = None
        if underlying > 0:
            if alert.option_type == "CALL":
                otm_pct = round((strike - underlying) / underlying * 100, 1) if strike > underlying else round((underlying - strike) / underlying * -100, 1)
            else:
                otm_pct = round((underlying - strike) / underlying * 100, 1) if underlying > strike else round((strike - underlying) / underlying * -100, 1)

        direction = "unclear"
        if alert.option_type == "CALL" and alert.volume > 0:
            direction = "bullish"
        elif alert.option_type == "PUT" and alert.volume > 0:
            direction = "bearish"

        contract_label = f"{alert.option_type} {alert.ticker} {alert.expiry} {strike}{'C' if alert.option_type == 'CALL' else 'P'}"

        normalized = {
            "ticker": alert.ticker,
            "option_type": alert.option_type,
            "strike": strike,
            "expiry": alert.expiry,
            "dte": alert.dte,
            "volume": volume,
            "open_interest": oi,
            "volume_oi_ratio": ratio,
            "bid": alert.bid,
            "ask": alert.ask,
            "mid_price": mid_price,
            "last_price": alert.last_price,
            "implied_volatility": alert.implied_volatility,
            "iv_change": alert.iv_change,
            "premium": alert.premium,
            "underlying_price": underlying,
            "underlying_move_5d": alert.underlying_move_5d,
            "otm_pct": otm_pct,
            "direction": direction,
            "contract_label": contract_label,
        }
        logger.info("contract_normalized", ticker=alert.ticker, contract=contract_label)
        return normalized


normalizer = OptionsContractNormalizer()
