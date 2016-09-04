from fcgiproto.constants import (
    FCGI_BEGIN_REQUEST, FCGI_PARAMS, FCGI_STDIN, FCGI_STDOUT, FCGI_END_REQUEST, FCGI_DATA,
    FCGI_FILTER, FCGI_AUTHORIZER, FCGI_ABORT_REQUEST, FCGI_REQUEST_COMPLETE)
from fcgiproto.events import (
    RequestDataEvent, RequestSecondaryDataEvent, RequestAbortEvent, RequestBeginEvent)
from fcgiproto.exceptions import ProtocolError
from fcgiproto.records import decode_name_value_pairs


class RequestState(object):
    __slots__ = ('state', 'role', 'flags', 'params_buffer')

    EXPECT_BEGIN_REQUEST = 1
    EXPECT_PARAMS = 2
    EXPECT_STDIN = 3
    EXPECT_DATA = 4
    EXPECT_STDOUT = 5
    EXPECT_END_REQUEST = 6
    FINISHED = 7
    state_names = {value: varname for varname, value in locals().items() if isinstance(value, int)}

    def __init__(self):
        self.state = RequestState.EXPECT_BEGIN_REQUEST
        self.role = self.flags = None
        self.params_buffer = bytearray()

    def receive_record(self, record):
        if record.record_type == FCGI_BEGIN_REQUEST:
            if self.state == RequestState.EXPECT_BEGIN_REQUEST:
                self.role = record.role
                self.flags = record.flags
                self.state = RequestState.EXPECT_PARAMS
                return None
        elif record.record_type == FCGI_PARAMS:
            if self.state == RequestState.EXPECT_PARAMS:
                if record.content:
                    self.params_buffer.extend(record.content)
                    return None
                else:
                    params = decode_name_value_pairs(self.params_buffer)
                    if self.role == FCGI_AUTHORIZER:
                        self.state = RequestState.EXPECT_STDOUT
                    else:
                        self.state = RequestState.EXPECT_STDIN

                    return RequestBeginEvent(record.request_id, self.role, self.flags, params)
        elif record.record_type == FCGI_STDIN:
            if self.state == RequestState.EXPECT_STDIN:
                if not record.content:
                    if self.role == FCGI_FILTER:
                        self.state = RequestState.EXPECT_DATA
                    else:
                        self.state = RequestState.EXPECT_STDOUT

                return RequestDataEvent(record.request_id, record.content)
        elif record.record_type == FCGI_DATA:
            if self.state == RequestState.EXPECT_DATA:
                if not record.content:
                    self.state = RequestState.EXPECT_STDOUT

                return RequestSecondaryDataEvent(record.request_id, record.content)
        elif record.record_type == FCGI_ABORT_REQUEST:
            if RequestState.EXPECT_BEGIN_REQUEST < self.state < RequestState.FINISHED:
                self.state = RequestState.EXPECT_END_REQUEST
                return RequestAbortEvent(record.request_id)

        raise ProtocolError('received unexpected %s record in the %s state' % (
            record.__class__.__name__, self.state_names[self.state]))

    def send_record(self, record):
        if record.record_type == FCGI_STDOUT:
            if self.state == RequestState.EXPECT_STDOUT:
                if not record.content:
                    self.state = RequestState.EXPECT_END_REQUEST

                return
        elif record.record_type == FCGI_END_REQUEST:
            # Only allow a normal request finish when it's expected
            if self.state == RequestState.EXPECT_END_REQUEST:
                if record.protocol_status == FCGI_REQUEST_COMPLETE:
                    self.state = RequestState.FINISHED
                    return
            elif self.state == RequestState.EXPECT_PARAMS:
                # Allow rejecting the request right after receiving it but not later
                if record.protocol_status != FCGI_REQUEST_COMPLETE:
                    self.state = RequestState.FINISHED
                    return

        raise ProtocolError('cannot send %s record in the %s state' % (
            record.__class__.__name__, self.state_names[self.state]))
