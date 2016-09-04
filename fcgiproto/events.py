from collections import OrderedDict

from fcgiproto.constants import FCGI_KEEP_CONN


class RequestEvent(object):
    """
    Base class for events that target a specific request.

    :ivar int request_id: identifier of the associated request
    """

    __slots__ = ('request_id',)

    def __init__(self, request_id):
        self.request_id = request_id


class RequestBeginEvent(RequestEvent):
    """
    Signals the application about a new incoming request.

    :ivar int request_id: identifier of the request
    :ivar int role: expected role of the application for the request
        one of (``FCGI_RESPONDER``, ``FCGI_AUTHORIZER``, ``FCGI_FILTER``)
    :ivar dict params: FCGI parameters for the request
    """

    __slots__ = ('role', 'keep_connection', 'params')

    def __init__(self, request_id, role, flags, params):
        super(RequestBeginEvent, self).__init__(request_id)
        self.role = role
        self.keep_connection = flags & FCGI_KEEP_CONN
        self.params = OrderedDict(params)


class RequestDataEvent(RequestEvent):
    """
    Contains body data for the specified request.

    An empty ``data`` argument signifies the end of the data stream.

    :ivar int request_id: identifier of the request
    :ivar bytes data: bytestring containing raw request data
    """

    __slots__ = ('data',)

    def __init__(self, request_id, data):
        super(RequestDataEvent, self).__init__(request_id)
        self.data = data


class RequestSecondaryDataEvent(RequestEvent):
    """
    Contains secondary data for the specified request.

    An empty ``data`` argument signifies the end of the data stream.

    These events are only received for the ``FCGI_FILTER`` role.

    :ivar int request_id: identifier of the request
    :ivar bytes data: bytestring containing raw secondary data
    """

    __slots__ = ('data',)

    def __init__(self, request_id, data):
        super(RequestSecondaryDataEvent, self).__init__(request_id)
        self.data = data


class RequestAbortEvent(RequestEvent):
    """Signals the application that the server wants the specified request aborted."""

    __slots__ = ()
