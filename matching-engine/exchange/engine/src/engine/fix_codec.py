"""FIX 4.4 message encoding/decoding.

Encodes internal models to FIX messages and decodes FIX messages to internal models.
Used internally for protocol representation — clients communicate via JSON over WebSocket,
and messages are translated to/from FIX format for logging and protocol correctness.
"""

from __future__ import annotations

import simplefix
from datetime import datetime, timezone

from engine.models import (
    ExecType,
    ExecutionReport,
    OrdStatus,
    OrdType,
    Order,
    Side,
    Trade,
)

# --- FIX Tag Constants ---
TAG_ACCOUNT = 1
TAG_AVG_PX = 6
TAG_BEGIN_STRING = 8
TAG_BODY_LENGTH = 9
TAG_CHECKSUM = 10
TAG_CL_ORD_ID = 11
TAG_CUM_QTY = 14
TAG_EXEC_ID = 17
TAG_LAST_PX = 31
TAG_LAST_QTY = 32
TAG_MSG_SEQ_NUM = 34
TAG_MSG_TYPE = 35
TAG_ORDER_ID = 37
TAG_ORDER_QTY = 38
TAG_ORD_STATUS = 39
TAG_ORD_TYPE = 40
TAG_PRICE = 44
TAG_SENDER_COMP_ID = 49
TAG_SENDING_TIME = 52
TAG_SIDE = 54
TAG_SYMBOL = 55
TAG_TARGET_COMP_ID = 56
TAG_TEXT = 58
TAG_TIME_IN_FORCE = 59
TAG_TRANSACT_TIME = 60
TAG_HANDL_INST = 21
TAG_EXEC_TYPE = 150
TAG_LEAVES_QTY = 151
TAG_ORD_REJ_REASON = 103

# MsgType values
MSGTYPE_NEW_ORDER_SINGLE = "D"
MSGTYPE_EXECUTION_REPORT = "8"

# Side mappings
_SIDE_TO_FIX = {Side.BUY: "1", Side.SELL: "2"}
_FIX_TO_SIDE = {"1": Side.BUY, "2": Side.SELL}

# OrdType mappings
_ORDTYPE_TO_FIX = {OrdType.MARKET: "1", OrdType.LIMIT: "2"}
_FIX_TO_ORDTYPE = {"1": OrdType.MARKET, "2": OrdType.LIMIT}

# OrdStatus mappings
_ORDSTATUS_TO_FIX = {
    OrdStatus.NEW: "0",
    OrdStatus.PARTIALLY_FILLED: "1",
    OrdStatus.FILLED: "2",
    OrdStatus.CANCELLED: "4",
    OrdStatus.REJECTED: "8",
}
_FIX_TO_ORDSTATUS = {v: k for k, v in _ORDSTATUS_TO_FIX.items()}

# ExecType mappings
_EXECTYPE_TO_FIX = {
    ExecType.NEW: "0",
    ExecType.TRADE: "F",
    ExecType.CANCELLED: "4",
    ExecType.REJECTED: "8",
}
_FIX_TO_EXECTYPE = {v: k for k, v in _EXECTYPE_TO_FIX.items()}

# --- Encoder ---


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


def encode_new_order_single(
    order: Order,
    sender: str = "CLIENT",
    target: str = "EXCHANGE",
    seq_num: int = 1,
) -> bytes:
    """Encode an Order as a FIX 4.4 NewOrderSingle (35=D) message."""
    msg = simplefix.FixMessage()
    msg.append_pair(TAG_BEGIN_STRING, "FIX.4.4")
    msg.append_pair(TAG_MSG_TYPE, MSGTYPE_NEW_ORDER_SINGLE)
    msg.append_pair(TAG_SENDER_COMP_ID, sender)
    msg.append_pair(TAG_TARGET_COMP_ID, target)
    msg.append_pair(TAG_MSG_SEQ_NUM, seq_num)
    msg.append_pair(TAG_SENDING_TIME, _utc_now_str())
    msg.append_pair(TAG_CL_ORD_ID, order.cl_ord_id)
    msg.append_pair(TAG_HANDL_INST, "1")  # Automated private
    msg.append_pair(TAG_ACCOUNT, order.account)
    msg.append_pair(TAG_SYMBOL, order.symbol)
    msg.append_pair(TAG_SIDE, _SIDE_TO_FIX[order.side])
    msg.append_pair(TAG_TRANSACT_TIME, _utc_now_str())
    msg.append_pair(TAG_ORDER_QTY, order.quantity)
    msg.append_pair(TAG_ORD_TYPE, _ORDTYPE_TO_FIX[order.ord_type])
    if order.ord_type == OrdType.LIMIT:
        msg.append_pair(TAG_PRICE, order.price)
    msg.append_pair(TAG_TIME_IN_FORCE, "0")  # DAY
    return msg.encode()


def encode_execution_report(
    report: ExecutionReport,
    sender: str = "EXCHANGE",
    target: str = "CLIENT",
    seq_num: int = 1,
) -> bytes:
    """Encode an ExecutionReport as a FIX 4.4 ExecutionReport (35=8) message."""
    msg = simplefix.FixMessage()
    msg.append_pair(TAG_BEGIN_STRING, "FIX.4.4")
    msg.append_pair(TAG_MSG_TYPE, MSGTYPE_EXECUTION_REPORT)
    msg.append_pair(TAG_SENDER_COMP_ID, sender)
    msg.append_pair(TAG_TARGET_COMP_ID, target)
    msg.append_pair(TAG_MSG_SEQ_NUM, seq_num)
    msg.append_pair(TAG_SENDING_TIME, _utc_now_str())
    msg.append_pair(TAG_ORDER_ID, report.order_id or "NONE")
    msg.append_pair(TAG_CL_ORD_ID, report.cl_ord_id)
    msg.append_pair(TAG_EXEC_ID, report.exec_id)
    msg.append_pair(TAG_EXEC_TYPE, _EXECTYPE_TO_FIX[report.exec_type])
    msg.append_pair(TAG_ORD_STATUS, _ORDSTATUS_TO_FIX[report.ord_status])
    msg.append_pair(TAG_SYMBOL, report.symbol)
    msg.append_pair(TAG_SIDE, _SIDE_TO_FIX[report.side])
    msg.append_pair(TAG_ORDER_QTY, report.quantity)
    if report.price > 0:
        msg.append_pair(TAG_PRICE, report.price)
    msg.append_pair(TAG_LEAVES_QTY, report.leaves_qty)
    msg.append_pair(TAG_CUM_QTY, report.cum_qty)
    msg.append_pair(TAG_AVG_PX, f"{report.avg_px:.2f}")
    if report.last_px > 0:
        msg.append_pair(TAG_LAST_PX, report.last_px)
    if report.last_qty > 0:
        msg.append_pair(TAG_LAST_QTY, report.last_qty)
    msg.append_pair(TAG_TRANSACT_TIME, _utc_now_str())
    if report.reject_reason:
        msg.append_pair(TAG_TEXT, report.reject_reason)
    return msg.encode()


# --- Decoder ---


def decode_new_order_single(raw: bytes) -> Order:
    """Decode a FIX 4.4 NewOrderSingle (35=D) message into an Order.

    Raises ValueError if the message is not a valid NewOrderSingle.
    """
    parser = simplefix.FixParser()
    parser.append_buffer(raw)
    msg = parser.get_message()
    if msg is None:
        raise ValueError("Could not parse FIX message")

    msg_type = _get_str(msg, TAG_MSG_TYPE)
    if msg_type != MSGTYPE_NEW_ORDER_SINGLE:
        raise ValueError(f"Expected MsgType=D, got MsgType={msg_type}")

    cl_ord_id = _get_str(msg, TAG_CL_ORD_ID)
    account = _get_str(msg, TAG_ACCOUNT, default="")
    symbol = _get_str(msg, TAG_SYMBOL)
    side = _FIX_TO_SIDE[_get_str(msg, TAG_SIDE)]
    ord_type = _FIX_TO_ORDTYPE[_get_str(msg, TAG_ORD_TYPE)]
    quantity = int(_get_str(msg, TAG_ORDER_QTY))

    price = 0
    if ord_type == OrdType.LIMIT:
        price = int(_get_str(msg, TAG_PRICE))

    return Order(
        cl_ord_id=cl_ord_id,
        account=account,
        symbol=symbol,
        side=side,
        ord_type=ord_type,
        price=price,
        quantity=quantity,
    )


def decode_execution_report(raw: bytes) -> ExecutionReport:
    """Decode a FIX 4.4 ExecutionReport (35=8) into an ExecutionReport.

    Raises ValueError if the message is not a valid ExecutionReport.
    """
    parser = simplefix.FixParser()
    parser.append_buffer(raw)
    msg = parser.get_message()
    if msg is None:
        raise ValueError("Could not parse FIX message")

    msg_type = _get_str(msg, TAG_MSG_TYPE)
    if msg_type != MSGTYPE_EXECUTION_REPORT:
        raise ValueError(f"Expected MsgType=8, got MsgType={msg_type}")

    return ExecutionReport(
        cl_ord_id=_get_str(msg, TAG_CL_ORD_ID),
        order_id=_get_str(msg, TAG_ORDER_ID),
        exec_id=_get_str(msg, TAG_EXEC_ID),
        exec_type=_FIX_TO_EXECTYPE[_get_str(msg, TAG_EXEC_TYPE)],
        ord_status=_FIX_TO_ORDSTATUS[_get_str(msg, TAG_ORD_STATUS)],
        symbol=_get_str(msg, TAG_SYMBOL),
        side=_FIX_TO_SIDE[_get_str(msg, TAG_SIDE)],
        price=int(_get_str(msg, TAG_PRICE, default="0")),
        quantity=int(_get_str(msg, TAG_ORDER_QTY)),
        leaves_qty=int(_get_str(msg, TAG_LEAVES_QTY)),
        cum_qty=int(_get_str(msg, TAG_CUM_QTY)),
        avg_px=float(_get_str(msg, TAG_AVG_PX)),
        last_px=int(_get_str(msg, TAG_LAST_PX, default="0")),
        last_qty=int(_get_str(msg, TAG_LAST_QTY, default="0")),
        reject_reason=_get_str(msg, TAG_TEXT, default=""),
    )


def _get_str(msg: simplefix.FixMessage, tag: int, default: str | None = None) -> str:
    """Get a FIX field as a string. Raises ValueError if missing and no default."""
    val = msg.get(tag)
    if val is None:
        if default is not None:
            return default
        raise ValueError(f"Missing required FIX tag {tag}")
    return val.decode() if isinstance(val, bytes) else str(val)


# --- Human-readable formatting ---


def fix_to_human(raw: bytes) -> str:
    """Convert raw FIX bytes to a human-readable pipe-delimited string."""
    return raw.decode("ascii", errors="replace").replace("\x01", "|")
