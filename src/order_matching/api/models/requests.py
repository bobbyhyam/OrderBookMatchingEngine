from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from order_matching.order import PRICE_NUMBER_OF_DIGITS


class SideStr(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    trader_id: str
    side: SideStr
    size: float = Field(gt=0)
    timestamp: datetime
    expiration: datetime | None = None


class LimitOrderRequest(OrderBase):
    order_type: Literal["limit"] = "limit"
    price: float = Field(gt=0)

    @field_validator("price")
    @classmethod
    def _check_price_tick(cls, price: float) -> float:
        exponent = Decimal(repr(price)).as_tuple().exponent
        if isinstance(exponent, int) and exponent < -PRICE_NUMBER_OF_DIGITS:
            raise PydanticCustomError(
                "price_tick",
                "price must be a multiple of the tick size {tick}",
                {"tick": 10**-PRICE_NUMBER_OF_DIGITS},
            )
        return price


class MarketOrderRequest(OrderBase):
    order_type: Literal["market"] = "market"


OrderRequest = Annotated[LimitOrderRequest | MarketOrderRequest, Field(discriminator="order_type")]


class PlaceRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "openapi_examples": {
                "two limit orders": {
                    "value": {
                        "orders": [
                            {
                                "order_type": "limit",
                                "order_id": "order_001",
                                "trader_id": "trader_alice",
                                "side": "BUY",
                                "size": 10.0,
                                "price": 100.50,
                                "timestamp": "2026-07-16T12:00:00",
                            },
                            {
                                "order_type": "limit",
                                "order_id": "order_002",
                                "trader_id": "trader_bob",
                                "side": "SELL",
                                "size": 5.0,
                                "price": 99.75,
                                "timestamp": "2026-07-16T12:00:01",
                            },
                        ]
                    }
                },
                "one market order": {
                    "value": {
                        "orders": [
                            {
                                "order_type": "market",
                                "order_id": "order_003",
                                "trader_id": "trader_charlie",
                                "side": "BUY",
                                "size": 15.0,
                                "timestamp": "2026-07-16T12:00:02",
                            }
                        ]
                    }
                },
            }
        },
    )
    orders: Annotated[list[OrderRequest], Field(min_length=1)]


class MatchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "openapi_examples": {
                "first": {"value": {"timestamp": "2026-07-16T12:00:00"}},
                "second": {"value": {"timestamp": "2026-07-16T14:30:00"}},
            }
        },
    )
    timestamp: datetime


class ResetRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "openapi_examples": {"fixed seed": {"value": {"seed": 42}}, "no seed, random state": {"value": {}}}
        },
    )
    seed: int | None = None
