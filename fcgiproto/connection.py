from collections import defaultdict

from fcgiproto.constants import (
    FCGI_REQUEST_COMPLETE, FCGI_GET_VALUES, FCGI_RESPONDER, FCGI_BEGIN_REQUEST, FCGI_UNKNOWN_ROLE)
from fcgiproto.records import (
    FCGIStdout, FCGIEndRequest, FCGIGetValuesResult, FCGIUnknownType, decode_record)
from fcgiproto.states import RequestState


class FastCGIConnection(object):
    """
    FastCGIConnection(roles=(FCGI_RESPONDER,), fcgi_values=None)

    FastCGI connection state machine.

    :param roles: iterable of allowed application roles (``FCGI_RESPONDER``, ``FCGI_AUTHORIZER``,
        ``FCGI_FILTER``)
    :param dict fcgi_values: dictionary of FastCGI management values (see the
        `FastCGI specification`_ for a list); keys and values must be unicode strings

    .. _FastCGI specification: https://htmlpreview.github.io/?https://github.com/FastCGI-Archives/\
        FastCGI.com/blob/master/docs/FastCGI%20Specification.html

    """

    __slots__ = ('roles', 'fcgi_values', '_input_buffer', '_output_buffer', '_request_states')

    def __init__(self, roles=(FCGI_RESPONDER,), fcgi_values=None):
        self.roles = frozenset(roles)
        self.fcgi_values = fcgi_values or {}
        self.fcgi_values.setdefault(u'FCGI_MPXS_CONNS', u'1')
        self._input_buffer = bytearray()
        self._output_buffer = bytearray()
        self._request_states = defaultdict(RequestState)

    def feed_data(self, data):
        """
        Feed data to the internal buffer of the connection.

        If there is enough data to generate one or more events, they will be added to the list
        returned from this call.

        Sometimes this call generates outgoing data so it is important to call
        :meth:`.data_to_send` afterwards and write those bytes to the output.

        :param bytes data: incoming data
        :raise fcgiproto.ProtocolError: if the protocol is violated
        :return: the list of generated FastCGI events
        :rtype: list

        """
        self._input_buffer.extend(data)
        events = []
        while True:
            record = decode_record(self._input_buffer)
            if record is None:
                return events

            if record.request_id:
                request_state = self._request_states[record.request_id]
                event = request_state.receive_record(record)
                if record.record_type == FCGI_BEGIN_REQUEST and record.role not in self.roles:
                    # Reject requests where the role isn't among our set of allowed roles
                    self._send_record(FCGIEndRequest(record.request_id, 0, FCGI_UNKNOWN_ROLE))
                elif event is not None:
                    events.append(event)
            else:
                if record.record_type == FCGI_GET_VALUES:
                    pairs = [(key, self.fcgi_values[key]) for key in record.keys
                             if key in self.fcgi_values]
                    self._send_record(FCGIGetValuesResult(pairs))
                else:
                    self._send_record(FCGIUnknownType(record.record_type))

    def data_to_send(self):
        """
        Return any data that is due to be sent to the other end.

        :rtype: bytes

        """
        data = bytes(self._output_buffer)
        del self._output_buffer[:]
        return data

    def send_headers(self, request_id, headers, status=None):
        """
        Send response headers for the given request.

        Header keys will be converted from unicode strings to bytestrings if necessary.
        Values will be converted from any type to bytestrings if necessary.

        :param int request_id: identifier of the request
        :param headers: an iterable of (key, value) tuples of bytestrings
        :param int status: the response status code, if not 200
        :raise fcgiproto.ProtocolError: if the protocol is violated

        """
        payload = bytearray()

        if status:
            payload.extend((u'Status: %d\r\n' % status).encode('ascii'))

        for key, value in headers:
            if not isinstance(key, bytes):
                raise TypeError('header keys must be bytestrings, not %s' % key.__class__.__name__)
            if not isinstance(value, bytes):
                raise TypeError('header values must be bytestrings, not %s' %
                                value.__class__.__name__)

            payload.extend(key + b': ' + value + b'\r\n')

        payload.extend(b'\r\n')
        record = FCGIStdout(request_id, payload)
        self._send_record(record)

    def send_data(self, request_id, data, end_request=False):
        """
        Send response body data for the given request.

        This method may be called several times before :meth:`.end_request`.

        :param int request_id: identifier of the request
        :param bytes data: request body data
        :param bool end_request: ``True`` to finish the request
        :raise fcgiproto.ProtocolError: if the protocol is violated

        """
        self._send_record(FCGIStdout(request_id, data))
        if end_request:
            self._send_record(FCGIStdout(request_id, b''))
            self._send_record(FCGIEndRequest(request_id, 0, FCGI_REQUEST_COMPLETE))

    def end_request(self, request_id):
        """
        Mark the given request finished.

        :param int request_id: identifier of the request
        :raise fcgiproto.ProtocolError: if the protocol is violated

        """
        self._send_record(FCGIEndRequest(request_id, 0, FCGI_REQUEST_COMPLETE))

    def _send_record(self, record):
        if record.request_id:
            request_state = self._request_states[record.request_id]
            request_state.send_record(record)
            if request_state.state == RequestState.FINISHED:
                del self._request_states[record.request_id]

        self._output_buffer.extend(record.encode())
