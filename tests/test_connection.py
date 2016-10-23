import pytest

from fcgiproto.connection import FastCGIConnection
from fcgiproto.constants import (
    FCGI_RESPONDER, FCGI_AUTHORIZER, FCGI_FILTER, FCGI_REQUEST_COMPLETE, FCGI_UNKNOWN_ROLE)
from fcgiproto.events import (
    RequestBeginEvent, RequestAbortEvent, RequestDataEvent, RequestSecondaryDataEvent)
from fcgiproto.records import (
    FCGIBeginRequest, FCGIStdin, FCGIParams, FCGIStdout, FCGIEndRequest, encode_name_value_pairs,
    FCGIAbortRequest, FCGIGetValues, FCGIGetValuesResult, FCGIUnknownType, FCGIData)


@pytest.fixture
def conn():
    return FastCGIConnection()


@pytest.mark.parametrize('send_status', [True, False])
def test_responder_request(conn, send_status):
    events = conn.feed_data(FCGIBeginRequest(1, FCGI_RESPONDER, 0).encode())
    assert len(events) == 0

    content = encode_name_value_pairs([('REQUEST_METHOD', 'GET'), ('CONTENT_LENGTH', '')])
    events = conn.feed_data(FCGIParams(1, content).encode())
    assert len(events) == 0

    events = conn.feed_data(FCGIParams(1, b'').encode())
    assert isinstance(events[0], RequestBeginEvent)

    events = conn.feed_data(FCGIStdin(1, b'content').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestDataEvent)

    events = conn.feed_data(FCGIStdin(1, b'').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestDataEvent)

    headers = [(b'Content-Length', b'7'), (b'Content-Type', b'text/plain')]
    conn.send_headers(1, headers, status=200 if send_status else None)
    expected_body = b'Content-Length: 7\r\nContent-Type: text/plain\r\n\r\n'
    if send_status:
        expected_body = b'Status: 200\r\n' + expected_body
    assert conn.data_to_send() == \
        FCGIStdout(1, expected_body).encode()

    conn.send_data(1, b'Cont')
    assert conn.data_to_send() == FCGIStdout(1, b'Cont').encode()

    conn.send_data(1, b'ent', end_request=True)
    assert conn.data_to_send() == FCGIStdout(1, b'ent').encode() + \
        FCGIStdout(1, b'').encode() + FCGIEndRequest(1, 0, FCGI_REQUEST_COMPLETE).encode()


def test_authorizer_request():
    conn = FastCGIConnection(roles=[FCGI_AUTHORIZER])
    events = conn.feed_data(FCGIBeginRequest(1, FCGI_AUTHORIZER, 0).encode())
    assert len(events) == 0

    content = encode_name_value_pairs([('REQUEST_METHOD', 'GET'), ('CONTENT_LENGTH', '')])
    events = conn.feed_data(FCGIParams(1, content).encode())
    assert len(events) == 0

    events = conn.feed_data(FCGIParams(1, b'').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestBeginEvent)

    headers = [(b'Content-Length', b'13'), (b'Content-Type', b'text/plain')]
    conn.send_headers(1, headers, status=403)
    assert conn.data_to_send() == \
        FCGIStdout(1, b'Status: 403\r\nContent-Length: 13\r\n'
                      b'Content-Type: text/plain\r\n\r\n').encode()

    conn.send_data(1, b'Access denied', end_request=True)
    assert conn.data_to_send() == \
        FCGIStdout(1, b'Access denied').encode() + FCGIStdout(1, b'').encode() + \
        FCGIEndRequest(1, 0, FCGI_REQUEST_COMPLETE).encode()


def test_filter_request():
    conn = FastCGIConnection(roles=[FCGI_FILTER])
    events = conn.feed_data(FCGIBeginRequest(1, FCGI_FILTER, 0).encode())
    assert len(events) == 0

    content = encode_name_value_pairs([('REQUEST_METHOD', 'GET'), ('CONTENT_LENGTH', '')])
    events = conn.feed_data(FCGIParams(1, content).encode())
    assert len(events) == 0

    events = conn.feed_data(FCGIParams(1, b'').encode())
    assert isinstance(events[0], RequestBeginEvent)

    events = conn.feed_data(FCGIStdin(1, b'content').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestDataEvent)

    events = conn.feed_data(FCGIStdin(1, b'').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestDataEvent)

    events = conn.feed_data(FCGIData(1, b'file data').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestSecondaryDataEvent)

    events = conn.feed_data(FCGIData(1, b'').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestSecondaryDataEvent)

    headers = [(b'Content-Length', b'9'), (b'Content-Type', b'application/octet-stream')]
    conn.send_headers(1, headers, status=404)
    assert conn.data_to_send() == \
        FCGIStdout(1, b'Status: 404\r\nContent-Length: 9\r\n'
                      b'Content-Type: application/octet-stream\r\n\r\n').\
        encode()

    conn.send_data(1, b'file data', end_request=True)
    assert conn.data_to_send() == FCGIStdout(1, b'file data').encode() + \
        FCGIStdout(1, b'').encode() + FCGIEndRequest(1, 0, FCGI_REQUEST_COMPLETE).encode()


def test_aborted_request(conn):
    events = conn.feed_data(FCGIBeginRequest(1, FCGI_RESPONDER, 0).encode())
    assert len(events) == 0

    content = encode_name_value_pairs([('REQUEST_METHOD', 'GET'), ('CONTENT_LENGTH', '')])
    events = conn.feed_data(FCGIParams(1, content).encode())
    assert len(events) == 0

    events = conn.feed_data(FCGIParams(1, b'').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestBeginEvent)

    events = conn.feed_data(FCGIStdin(1, b'').encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestDataEvent)

    events = conn.feed_data(FCGIAbortRequest(1).encode())
    assert len(events) == 1
    assert isinstance(events[0], RequestAbortEvent)

    conn.end_request(1)
    assert conn.data_to_send() == FCGIEndRequest(1, 0, FCGI_REQUEST_COMPLETE).encode()


def test_unknown_role(conn):
    events = conn.feed_data(FCGIBeginRequest(1, FCGI_AUTHORIZER, 0).encode())
    assert len(events) == 0
    assert conn.data_to_send() == FCGIEndRequest(1, 0, FCGI_UNKNOWN_ROLE).encode()


def test_unknown_record_type(conn):
    events = conn.feed_data(b'\x01\x0c\x00\x00\x00\x00\x00\x00')
    assert len(events) == 0
    assert conn.data_to_send() == FCGIUnknownType(12).encode()


def test_get_values(conn):
    keys = ['FCGI_MPXS_CONNS', 'FCGI_OTHER_KEY']
    values = [('FCGI_MPXS_CONNS', '1')]
    events = conn.feed_data(FCGIGetValues(keys).encode())
    assert len(events) == 0
    assert conn.data_to_send() == FCGIGetValuesResult(values).encode()


def test_send_headers_invalid_key(conn):
    headers = [(1, b'value')]
    exc = pytest.raises(TypeError, conn.send_headers, 1, headers)
    assert str(exc.value) == 'header keys must be bytestrings, not int'


def test_send_headers_invalid_value(conn):
    headers = [(b'Invalid', 1)]
    exc = pytest.raises(TypeError, conn.send_headers, 1, headers)
    assert str(exc.value) == 'header values must be bytestrings, not int'
