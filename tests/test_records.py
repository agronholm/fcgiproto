import pytest

from fcgiproto.records import (
    encode_name_value_pairs, decode_name_value_pairs, decode_record, FCGIStdin, FCGIBeginRequest,
    FCGIEndRequest, FCGIUnknownType, FCGIStdout, FCGIGetValues, FCGIGetValuesResult,
    FCGIAbortRequest)
from fcgiproto.exceptions import ProtocolError


def test_encode_simple_record():
    record = FCGIStdout(5, b'data')
    assert record.encode() == b'\x01\x06\x00\x05\x00\x04\x00\x00data'


def test_parse_get_values():
    buffer = bytearray(b'\x03\x00FOO\x03\x00BAR')
    record = FCGIGetValues.parse(0, buffer)
    assert record.keys == ['FOO', 'BAR']


def test_encode_get_values():
    keys = ['FOO', 'BAR']
    record = FCGIGetValues(keys)
    assert record.encode() == b'\x01\x09\x00\x00\x00\x0a\x00\x00\x03\x00FOO\x03\x00BAR'


def test_parse_get_values_result():
    buffer = bytearray(b'\x03\x03FOOabc\x03\x03BARxyz')
    record = FCGIGetValuesResult.parse(0, buffer)
    assert record.values == [('FOO', 'abc'), ('BAR', 'xyz')]


def test_encode_get_values_result():
    values = [('FOO', 'abc'), ('BAR', 'xyz')]
    record = FCGIGetValuesResult(values)
    assert record.encode() == b'\x01\x0a\x00\x00\x00\x10\x00\x00\x03\x03FOOabc\x03\x03BARxyz'


def test_parse_begin_request():
    buffer = bytearray(b'\x00\x01\x01\x00\x00\x00\x00\x00')
    record = FCGIBeginRequest.parse(5, buffer)
    assert record.request_id == 5
    assert record.role == 1
    assert record.flags == 1


def test_encode_begin_request():
    record = FCGIBeginRequest(5, 1, 1)
    assert record.encode() == b'\x01\x01\x00\x05\x00\x08\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00'


def test_encode_abort_request():
    record = FCGIAbortRequest(5)
    assert record.encode() == b'\x01\x02\x00\x05\x00\x00\x00\x00'


def test_parse_abort_request():
    buffer = bytearray(b'')
    record = FCGIAbortRequest.parse(5, buffer)
    assert record.request_id == 5


def test_parse_end_request():
    buffer = bytearray(b'\x00\x01\x00\x01\x02\x00\x00\x00')
    record = FCGIEndRequest.parse(5, buffer)
    assert record.request_id == 5
    assert record.app_status == 65537
    assert record.protocol_status == 2


def test_encode_end_request():
    record = FCGIEndRequest(5, 65537, 2)
    assert record.encode() == b'\x01\x03\x00\x05\x00\x08\x00\x00\x00\x01\x00\x01\x02\x00\x00\x00'


def test_encode_unknown_type():
    record = FCGIUnknownType(12)
    assert record.encode() == b'\x01\x0b\x00\x00\x00\x08\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00'


@pytest.mark.parametrize('data, expected', [
    (b'\x03\x06foobarbar\x01\x03Xxyz', [(u'foo', u'barbar'), ('X', 'xyz')]),
    (b'\x03\x80\x01\x00\x00foo' + b'x' * 65536, [(u'foo', u'x' * 65536)]),
    (b'\x80\x01\x00\x00\x03' + b'x' * 65536 + b'foo', [(u'x' * 65536, 'foo')]),
    (b'\x80\x01\x00\x00\x80\x01\x00\x00' + b'x' * 65536 + b'y' * 65536,
     [('x' * 65536, 'y' * 65536)])
], ids=['short_both', 'long_value', 'long_name', 'long_both'])
def test_decode_name_value_pairs(data, expected):
    buffer = bytearray(data)
    assert decode_name_value_pairs(buffer) == expected


@pytest.mark.parametrize('data, message', [
    (b'\x80\x00\x00', 'not enough data to decode name length in name-value pair'),
    (b'\x03', 'not enough data to decode value length in name-value pair'),
    (b'\x03\x06foo', 'name/value data missing from buffer')
], ids=['name_missing', 'value_missing', 'content_missing'])
def test_decode_name_value_pairs_incomplete(data, message):
    buffer = bytearray(data)
    exc = pytest.raises(ProtocolError, decode_name_value_pairs, buffer)
    assert str(exc.value).endswith(message)


@pytest.mark.parametrize('pairs, expected', [
    ([(u'foo', u'barbar'), (u'X', u'xyz')], b'\x03\x06foobarbar\x01\x03Xxyz'),
    ([(u'foo', u'x' * 65536)], b'\x03\x80\x01\x00\x00foo' + b'x' * 65536),
    ([(u'x' * 65536, u'foo')], b'\x80\x01\x00\x00\x03' + b'x' * 65536 + b'foo'),
    ([(u'x' * 65536, u'y' * 65536)],
     b'\x80\x01\x00\x00\x80\x01\x00\x00' + b'x' * 65536 + b'y' * 65536)
], ids=['short_both', 'long_value', 'long_name', 'long_both'])
def test_encode_name_value_pairs(pairs, expected):
    assert encode_name_value_pairs(pairs) == expected


def test_decode_record():
    buffer = bytearray(b'\x01\x05\x00\x01\x00\x07\x00\x00content')
    record = decode_record(buffer)
    assert isinstance(record, FCGIStdin)
    assert record.request_id == 1
    assert record.content == b'content'


def test_decode_record_incomplete():
    buffer = bytearray(b'\x01\x05\x00\x01\x00\x07\x00\x00conten')
    assert decode_record(buffer) is None


def test_decode_record_wrong_version():
    buffer = bytearray(b'\x02\x01\x00\x01\x00\x00\x00\x00')
    exc = pytest.raises(ProtocolError, decode_record, buffer)
    assert str(exc.value).endswith('unexpected protocol version: 2')


def test_decode_unknown_record_type():
    buffer = bytearray(b'\x01\x0c\x01\x00\x00\x00\x00\x00')
    exc = pytest.raises(ProtocolError, decode_record, buffer)
    assert str(exc.value).endswith('unknown record type: 12')
