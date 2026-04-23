"""Tests for FIX 4.4 message encoding/decoding."""

import pytest
import simplefix

from engine.fix_codec import (
    decode_execution_report,
    decode_new_order_single,
    encode_execution_report,
    encode_new_order_single,
    fix_to_human,
    _get_str,
    TAG_BEGIN_STRING,
    TAG_BODY_LENGTH,
    TAG_CHECKSUM,
    TAG_MSG_TYPE,
    TAG_CL_ORD_ID,
    TAG_SYMBOL,
    TAG_SIDE,
    TAG_ORD_TYPE,
    TAG_ORDER_QTY,
    TAG_PRICE,
    TAG_ORDER_ID,
    TAG_EXEC_ID,
    TAG_EXEC_TYPE,
    TAG_ORD_STATUS,
    TAG_LEAVES_QTY,
    TAG_CUM_QTY,
    TAG_AVG_PX,
    TAG_LAST_PX,
    TAG_LAST_QTY,
    TAG_TEXT,
    TAG_ACCOUNT,
)
from engine.models import (
    ExecType,
    ExecutionReport,
    OrdStatus,
    OrdType,
    Order,
    Side,
)


def make_limit_buy_order() -> Order:
    return Order(
        cl_ord_id="C-001",
        account="ACC1",
        symbol="FPT",
        side=Side.BUY,
        ord_type=OrdType.LIMIT,
        price=55000,
        quantity=200,
    )


def make_market_sell_order() -> Order:
    return Order(
        cl_ord_id="C-002",
        account="ACC2",
        symbol="ACB",
        side=Side.SELL,
        ord_type=OrdType.MARKET,
        price=0,
        quantity=100,
    )


def make_new_exec_report() -> ExecutionReport:
    return ExecutionReport(
        cl_ord_id="C-001",
        order_id="ORD-FPT-1",
        exec_id="EXEC-FPT-1",
        exec_type=ExecType.NEW,
        ord_status=OrdStatus.NEW,
        symbol="FPT",
        side=Side.BUY,
        price=55000,
        quantity=200,
        leaves_qty=200,
        cum_qty=0,
        avg_px=0.0,
    )


def make_trade_exec_report() -> ExecutionReport:
    return ExecutionReport(
        cl_ord_id="C-001",
        order_id="ORD-FPT-1",
        exec_id="EXEC-FPT-2",
        exec_type=ExecType.TRADE,
        ord_status=OrdStatus.FILLED,
        symbol="FPT",
        side=Side.BUY,
        price=55000,
        quantity=200,
        leaves_qty=0,
        cum_qty=200,
        avg_px=55000.0,
        last_px=55000,
        last_qty=200,
    )


def make_rejected_exec_report() -> ExecutionReport:
    return ExecutionReport(
        cl_ord_id="C-003",
        order_id="",
        exec_id="EXEC-REJ-1",
        exec_type=ExecType.REJECTED,
        ord_status=OrdStatus.REJECTED,
        symbol="FPT",
        side=Side.BUY,
        price=99999,
        quantity=200,
        leaves_qty=0,
        cum_qty=0,
        avg_px=0.0,
        reject_reason="Price 99999 above ceiling 75000",
    )


def _parse(raw: bytes) -> simplefix.FixMessage:
    parser = simplefix.FixParser()
    parser.append_buffer(raw)
    return parser.get_message()


class TestEncodeNewOrderSingle:
    def test_limit_buy(self):
        order = make_limit_buy_order()
        raw = encode_new_order_single(order)
        msg = _parse(raw)

        assert msg.get(TAG_BEGIN_STRING) == b"FIX.4.4"
        assert msg.get(TAG_MSG_TYPE) == b"D"
        assert msg.get(TAG_CL_ORD_ID) == b"C-001"
        assert msg.get(TAG_ACCOUNT) == b"ACC1"
        assert msg.get(TAG_SYMBOL) == b"FPT"
        assert msg.get(TAG_SIDE) == b"1"  # BUY
        assert msg.get(TAG_ORD_TYPE) == b"2"  # LIMIT
        assert msg.get(TAG_ORDER_QTY) == b"200"
        assert msg.get(TAG_PRICE) == b"55000"

    def test_market_sell(self):
        order = make_market_sell_order()
        raw = encode_new_order_single(order)
        msg = _parse(raw)

        assert msg.get(TAG_SYMBOL) == b"ACB"
        assert msg.get(TAG_SIDE) == b"2"  # SELL
        assert msg.get(TAG_ORD_TYPE) == b"1"  # MARKET
        assert msg.get(TAG_PRICE) is None  # No price for market orders

    def test_has_body_length_and_checksum(self):
        order = make_limit_buy_order()
        raw = encode_new_order_single(order)
        msg = _parse(raw)

        assert msg.get(TAG_BODY_LENGTH) is not None
        assert msg.get(TAG_CHECKSUM) is not None


class TestEncodeExecutionReport:
    def test_new_report(self):
        report = make_new_exec_report()
        raw = encode_execution_report(report)
        msg = _parse(raw)

        assert msg.get(TAG_MSG_TYPE) == b"8"
        assert msg.get(TAG_ORDER_ID) == b"ORD-FPT-1"
        assert msg.get(TAG_CL_ORD_ID) == b"C-001"
        assert msg.get(TAG_EXEC_ID) == b"EXEC-FPT-1"
        assert msg.get(TAG_EXEC_TYPE) == b"0"  # NEW
        assert msg.get(TAG_ORD_STATUS) == b"0"  # NEW
        assert msg.get(TAG_SYMBOL) == b"FPT"
        assert msg.get(TAG_SIDE) == b"1"  # BUY
        assert msg.get(TAG_LEAVES_QTY) == b"200"
        assert msg.get(TAG_CUM_QTY) == b"0"
        assert msg.get(TAG_AVG_PX) == b"0.00"
        assert msg.get(TAG_LAST_PX) is None  # No fill
        assert msg.get(TAG_LAST_QTY) is None

    def test_trade_report(self):
        report = make_trade_exec_report()
        raw = encode_execution_report(report)
        msg = _parse(raw)

        assert msg.get(TAG_EXEC_TYPE) == b"F"  # TRADE
        assert msg.get(TAG_ORD_STATUS) == b"2"  # FILLED
        assert msg.get(TAG_LEAVES_QTY) == b"0"
        assert msg.get(TAG_CUM_QTY) == b"200"
        assert msg.get(TAG_AVG_PX) == b"55000.00"
        assert msg.get(TAG_LAST_PX) == b"55000"
        assert msg.get(TAG_LAST_QTY) == b"200"

    def test_rejected_report_includes_text(self):
        report = make_rejected_exec_report()
        raw = encode_execution_report(report)
        msg = _parse(raw)

        assert msg.get(TAG_EXEC_TYPE) == b"8"  # REJECTED
        assert msg.get(TAG_ORD_STATUS) == b"8"  # REJECTED
        assert msg.get(TAG_TEXT) == b"Price 99999 above ceiling 75000"


class TestDecodeNewOrderSingle:
    def test_decode_limit_buy(self):
        original = make_limit_buy_order()
        raw = encode_new_order_single(original)
        decoded = decode_new_order_single(raw)

        assert decoded.cl_ord_id == "C-001"
        assert decoded.account == "ACC1"
        assert decoded.symbol == "FPT"
        assert decoded.side == Side.BUY
        assert decoded.ord_type == OrdType.LIMIT
        assert decoded.price == 55000
        assert decoded.quantity == 200

    def test_decode_market_sell(self):
        original = make_market_sell_order()
        raw = encode_new_order_single(original)
        decoded = decode_new_order_single(raw)

        assert decoded.cl_ord_id == "C-002"
        assert decoded.symbol == "ACB"
        assert decoded.side == Side.SELL
        assert decoded.ord_type == OrdType.MARKET
        assert decoded.price == 0
        assert decoded.quantity == 100

    def test_decode_invalid_bytes(self):
        with pytest.raises(ValueError, match="Could not parse"):
            decode_new_order_single(b"garbage data")

    def test_decode_wrong_msg_type(self):
        report = make_new_exec_report()
        raw = encode_execution_report(report)
        with pytest.raises(ValueError, match="Expected MsgType=D"):
            decode_new_order_single(raw)


class TestDecodeExecutionReport:
    def test_decode_new_report(self):
        original = make_new_exec_report()
        raw = encode_execution_report(original)
        decoded = decode_execution_report(raw)

        assert decoded.cl_ord_id == "C-001"
        assert decoded.order_id == "ORD-FPT-1"
        assert decoded.exec_id == "EXEC-FPT-1"
        assert decoded.exec_type == ExecType.NEW
        assert decoded.ord_status == OrdStatus.NEW
        assert decoded.symbol == "FPT"
        assert decoded.side == Side.BUY
        assert decoded.quantity == 200
        assert decoded.leaves_qty == 200
        assert decoded.cum_qty == 0
        assert decoded.avg_px == 0.0

    def test_decode_trade_report(self):
        original = make_trade_exec_report()
        raw = encode_execution_report(original)
        decoded = decode_execution_report(raw)

        assert decoded.exec_type == ExecType.TRADE
        assert decoded.ord_status == OrdStatus.FILLED
        assert decoded.last_px == 55000
        assert decoded.last_qty == 200
        assert decoded.leaves_qty == 0
        assert decoded.cum_qty == 200
        assert decoded.avg_px == 55000.0

    def test_decode_rejected_report(self):
        original = make_rejected_exec_report()
        raw = encode_execution_report(original)
        decoded = decode_execution_report(raw)

        assert decoded.exec_type == ExecType.REJECTED
        assert decoded.reject_reason == "Price 99999 above ceiling 75000"

    def test_decode_wrong_msg_type(self):
        order = make_limit_buy_order()
        raw = encode_new_order_single(order)
        with pytest.raises(ValueError, match="Expected MsgType=8"):
            decode_execution_report(raw)


class TestRoundTrip:
    def test_order_round_trip(self):
        """encode → decode → compare all fields."""
        original = make_limit_buy_order()
        raw = encode_new_order_single(original)
        decoded = decode_new_order_single(raw)

        assert decoded.cl_ord_id == original.cl_ord_id
        assert decoded.account == original.account
        assert decoded.symbol == original.symbol
        assert decoded.side == original.side
        assert decoded.ord_type == original.ord_type
        assert decoded.price == original.price
        assert decoded.quantity == original.quantity

    def test_exec_report_round_trip(self):
        """encode → decode → compare all fields."""
        original = make_trade_exec_report()
        raw = encode_execution_report(original)
        decoded = decode_execution_report(raw)

        assert decoded.cl_ord_id == original.cl_ord_id
        assert decoded.order_id == original.order_id
        assert decoded.exec_id == original.exec_id
        assert decoded.exec_type == original.exec_type
        assert decoded.ord_status == original.ord_status
        assert decoded.symbol == original.symbol
        assert decoded.side == original.side
        assert decoded.quantity == original.quantity
        assert decoded.leaves_qty == original.leaves_qty
        assert decoded.cum_qty == original.cum_qty
        assert abs(decoded.avg_px - original.avg_px) < 0.01
        assert decoded.last_px == original.last_px
        assert decoded.last_qty == original.last_qty


class TestChecksum:
    def test_checksum_valid(self):
        """Verify encoded message has valid 3-digit checksum."""
        raw = encode_new_order_single(make_limit_buy_order())
        # Checksum is the last field: 10=XXX|
        # Sum all bytes before 10= field, mod 256
        parts = raw.split(b"10=")
        body = parts[0]
        checksum_str = parts[1].rstrip(b"\x01").decode()
        assert len(checksum_str) == 3
        expected = sum(body) % 256
        assert int(checksum_str) == expected

    def test_body_length_valid(self):
        """Verify BodyLength(9) is correctly calculated."""
        raw = encode_new_order_single(make_limit_buy_order())
        # Body length = bytes from after 9=NNN| to before 10=XXX|
        parts = raw.split(b"\x01")
        # Find the 9= field
        body_len_val = None
        body_start_idx = None
        for i, part in enumerate(parts):
            if part.startswith(b"9="):
                body_len_val = int(part[2:])
                body_start_idx = i + 1
                break

        assert body_len_val is not None
        # Reconstruct body bytes (between 9= field and 10= field)
        body_parts = []
        for part in parts[body_start_idx:]:
            if part.startswith(b"10="):
                break
            body_parts.append(part)
        # Add back SOH delimiters
        body_bytes = b"\x01".join(body_parts) + b"\x01"
        assert len(body_bytes) == body_len_val


class TestHumanReadable:
    def test_fix_to_human(self):
        raw = encode_new_order_single(make_limit_buy_order())
        human = fix_to_human(raw)
        assert "|" in human
        assert "35=D" in human
        assert "55=FPT" in human
        assert "\x01" not in human
