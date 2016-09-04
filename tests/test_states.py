import pytest

from fcgiproto.constants import (
    FCGI_REQUEST_COMPLETE, FCGI_RESPONDER, FCGI_AUTHORIZER, FCGI_FILTER, FCGI_UNKNOWN_ROLE)
from fcgiproto.events import (
    RequestDataEvent, RequestAbortEvent, RequestBeginEvent, RequestSecondaryDataEvent)
from fcgiproto.exceptions import ProtocolError
from fcgiproto.records import (
    FCGIStdin, FCGIData, FCGIAbortRequest, FCGIStdout, FCGIEndRequest, FCGIBeginRequest,
    FCGIParams, encode_name_value_pairs)
from fcgiproto.states import RequestState

begin_record = FCGIBeginRequest(1, FCGI_RESPONDER, 0)
params_record = FCGIParams(1, encode_name_value_pairs([('NAME', 'VALUE')]))
params_end_record = FCGIParams(1, b'')
stdin_record = FCGIStdin(1, b'')
data_record = FCGIData(1, b'')
abort_record = FCGIAbortRequest(1)
stdout_record = FCGIStdout(1, b'content')
stdout_end_record = FCGIStdout(1, b'')
end_record = FCGIEndRequest(1, 0, FCGI_REQUEST_COMPLETE)
end_record_reject = FCGIEndRequest(1, 0, FCGI_UNKNOWN_ROLE)


class BaseStateTests(object):
    possible_states = {RequestState.EXPECT_BEGIN_REQUEST,
                       RequestState.EXPECT_PARAMS,
                       RequestState.EXPECT_STDIN,
                       RequestState.EXPECT_DATA,
                       RequestState.EXPECT_STDOUT,
                       RequestState.EXPECT_END_REQUEST,
                       RequestState.FINISHED}
    role = None

    @pytest.mark.parametrize('allowed_states, record, expected_event_class', [
        ([RequestState.EXPECT_BEGIN_REQUEST], begin_record, type(None)),
        ([RequestState.EXPECT_PARAMS], params_record, type(None)),
        ([RequestState.EXPECT_PARAMS], params_end_record, RequestBeginEvent),
        ([RequestState.EXPECT_STDIN], stdin_record, RequestDataEvent),
        ([RequestState.EXPECT_DATA], data_record, RequestSecondaryDataEvent),
        ([RequestState.EXPECT_PARAMS,
          RequestState.EXPECT_STDIN,
          RequestState.EXPECT_DATA,
          RequestState.EXPECT_STDOUT,
          RequestState.EXPECT_END_REQUEST], abort_record, RequestAbortEvent),
        ([], stdout_record, type(None))
    ], ids=['begin', 'params', 'params_end', 'stdin', 'data', 'abort', 'stdout'])
    def test_receive_record(self, allowed_states, record, expected_event_class):
        for state_num in sorted(self.possible_states):
            state = RequestState()
            state.role = self.role
            state.state = state_num
            state.flags = 0
            if state_num in allowed_states:
                event = state.receive_record(record)
                assert isinstance(event, expected_event_class)
            else:
                pytest.raises(ProtocolError, state.receive_record, record)

    @pytest.mark.parametrize('allowed_states, record, expected_end_state', [
        ([RequestState.EXPECT_STDOUT], stdout_record, RequestState.EXPECT_STDOUT),
        ([RequestState.EXPECT_STDOUT], stdout_end_record, RequestState.EXPECT_END_REQUEST),
        ([RequestState.EXPECT_END_REQUEST], end_record, RequestState.FINISHED),
        ([RequestState.EXPECT_PARAMS], end_record_reject, RequestState.FINISHED),
        ([], stdin_record, RequestState.EXPECT_BEGIN_REQUEST),
    ], ids=['stdout', 'stdout_end', 'endrequest', 'rejectrequest', 'stdin'])
    def test_send_record(self, allowed_states, record, expected_end_state):
        for state_num in sorted(self.possible_states):
            state = RequestState()
            state.role = self.role
            state.state = state_num
            state.flags = 0
            if state_num in allowed_states:
                state.send_record(record)
                assert state.state == expected_end_state
            else:
                pytest.raises(ProtocolError, state.send_record, record)


class TestResponder(BaseStateTests):
    role = FCGI_RESPONDER
    possible_states = BaseStateTests.possible_states - {RequestState.EXPECT_DATA}


class TestAuthorizer(BaseStateTests):
    role = FCGI_AUTHORIZER
    possible_states = (BaseStateTests.possible_states -
                       {RequestState.EXPECT_STDIN, RequestState.EXPECT_DATA})


class TestFilter(BaseStateTests):
    role = FCGI_FILTER
