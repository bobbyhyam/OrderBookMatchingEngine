import math
from dataclasses import dataclass, field
from datetime import datetime

from order_matching.enums import Execution, Side, Status

PRICE_NUMBER_OF_DIGITS = 2


@dataclass(kw_only=True)
class Order:
    """Single order base storage class."""

    side: Side
    price: float
    size: float
    timestamp: datetime
    order_id: str
    trader_id: str
    execution: Execution
    expiration: datetime = datetime.max
    status: Status = Status.OPEN
    price_number_of_digits: int = PRICE_NUMBER_OF_DIGITS

    def __post_init__(self) -> None:
        rounded_price = round(number=self.price, ndigits=self.price_number_of_digits)
        # Rounding only absorbs binary float noise (e.g. 0.1 + 0.2); a genuinely off-tick price is rejected so that
        # it can never be moved across the counterparty's limit or down to zero.
        if not math.isclose(rounded_price, self.price, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(
                f"Price {self.price} is not a multiple of the tick size {10**-self.price_number_of_digits}"
            )
        self.price = rounded_price


@dataclass(kw_only=True)
class LimitOrder(Order):
    """Single limit order storage class."""

    execution: Execution = field(init=False, default=Execution.LIMIT)


@dataclass(kw_only=True)
class MarketOrder(Order):
    """Single market order storage class."""

    execution: Execution = field(init=False, default=Execution.MARKET)
    price: float = field(init=False)

    def __post_init__(self) -> None:
        self.price = 0 if self.side == Side.SELL else float("inf")
