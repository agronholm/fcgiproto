class ProtocolError(Exception):
    """Raised by the state machine when the FastCGI protocol is being violated."""

    def __init__(self, message):
        super(ProtocolError, self).__init__('FastCGI protocol violation: %s' % message)
