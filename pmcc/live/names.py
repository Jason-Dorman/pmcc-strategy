"""Names and formats the live wheel's modules share, so each is said once."""

from pmcc.domain.instruments import Right
from pmcc.domain.money import Money, Price

# Where the order page puts Sanji's files and ours, besides the repo root (LD-04).
SANJI_DIR = "mkt"
ORDERS = "open_orders.json"

# The order language's word for each right ("put", "call"); Right's own values are "P" and "C".
RIGHT_NAMES = {Right.PUT: "put", Right.CALL: "call"}


def dollars(amount: Price | Money) -> str:
    """`162.83`: two places, no sign or symbol, as the run log and the reports write money."""
    return f"{amount.to_dollars():.2f}"


def quote_dollars(price: Price) -> str:
    """`1.075`: a quote's dollars, two places at least and four at most, so a mid that falls on
    a half cent is written exactly."""
    whole, _, places = f"{price.to_dollars():.4f}".partition(".")
    return f"{whole}.{places.rstrip('0').ljust(2, '0')}"
