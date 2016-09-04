from typing import Dict
from typing import List, Iterable, Tuple, Any
from typing import Set

from fcgiproto.constants import FCGI_RESPONDER
from fcgiproto.events import RequestEvent
from fcgiproto.records import FCGIRecord
from fcgiproto.states import RequestState


class FastCGIConnection:
    def __init__(self, roles: Iterable[int] = (FCGI_RESPONDER,),
                 fcgi_values: Dict[str, str] = None) -> None:
        self.roles = None  # type: Set[int]
        self.fcgi_values = None  # type: Dict[str, str]
        self._input_buffer = None  # type: bytearray
        self._output_buffer = None  # type: bytearray
        self._request_states = None  # type: Dict[int, RequestState]

    def feed_data(self, data: bytes) -> List[RequestEvent]:
        ...

    def data_to_send(self) -> bytes:
        ...

    def send_headers(self, request_id: int, headers: Iterable[Tuple[bytes, bytes]],
                     status: int = None) -> None:
        ...

    def send_data(self, request_id: int, data: bytes, end_request: bool = False) -> None:
        ...

    def end_request(self, request_id: int) -> None:
        ...

    def _send_record(self, record: FCGIRecord) -> None:
        ...
