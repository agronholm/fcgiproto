from struct import Struct

from fcgiproto.constants import (
    FCGI_BEGIN_REQUEST, FCGI_PARAMS, FCGI_END_REQUEST, FCGI_UNKNOWN_TYPE, FCGI_ABORT_REQUEST,
    FCGI_STDOUT, FCGI_STDIN, FCGI_STDERR, FCGI_DATA, FCGI_GET_VALUES, FCGI_GET_VALUES_RESULT)
from fcgiproto.exceptions import ProtocolError

headers_struct = Struct('>BBHHBx')
length4_struct = Struct('>I')


class FCGIRecord(object):
    __slots__ = ('request_id',)

    struct = Struct('')  # type: Struct
    record_type = None  # type: int

    def __init__(self, request_id):
        self.request_id = request_id

    @classmethod
    def parse(cls, request_id, content):
        fields = cls.struct.unpack(content)
        return cls(request_id, *fields)

    def encode_header(self, content):
        return headers_struct.pack(1, self.record_type, self.request_id, len(content), 0)

    def encode(self):  # pragma: no cover
        raise NotImplementedError


class FCGIBytestreamRecord(FCGIRecord):
    __slots__ = ('content',)

    def __init__(self, request_id, content):
        super(FCGIBytestreamRecord, self).__init__(request_id)
        self.content = content

    @classmethod
    def parse(cls, request_id, content):
        return cls(request_id, bytes(content))

    def encode(self):
        return self.encode_header(self.content) + self.content


class FCGIUnknownManagementRecord(FCGIRecord):
    def __init__(self, record_type):
        super(FCGIUnknownManagementRecord, self).__init__(0)
        self.record_type = record_type


class FCGIGetValues(FCGIRecord):
    __slots__ = ('keys',)

    record_type = FCGI_GET_VALUES

    def __init__(self, keys):
        super(FCGIGetValues, self).__init__(0)
        self.keys = keys

    @classmethod
    def parse(cls, request_id, content):
        assert request_id == 0
        keys = [key for key, value in decode_name_value_pairs(content)]
        return cls(keys)

    def encode(self):
        pairs = [(key, '') for key in self.keys]
        content = encode_name_value_pairs(pairs)
        return self.encode_header(content) + content


class FCGIGetValuesResult(FCGIRecord):
    __slots__ = ('values',)

    record_type = FCGI_GET_VALUES_RESULT

    def __init__(self, values):
        super(FCGIGetValuesResult, self).__init__(0)
        self.values = values

    @classmethod
    def parse(cls, request_id, content):
        assert request_id == 0
        values = decode_name_value_pairs(content)
        return cls(values)

    def encode(self):
        content = encode_name_value_pairs(self.values)
        return self.encode_header(content) + content


class FCGIUnknownType(FCGIRecord):
    __slots__ = ('type',)

    struct = Struct('>B7x')
    record_type = FCGI_UNKNOWN_TYPE

    def __init__(self, type):
        assert type > FCGI_UNKNOWN_TYPE
        super(FCGIUnknownType, self).__init__(0)
        self.type = type

    def encode(self):
        content = self.struct.pack(self.type)
        return self.encode_header(content) + content


class FCGIBeginRequest(FCGIRecord):
    __slots__ = ('role', 'flags')

    struct = Struct('>HB5x')
    record_type = FCGI_BEGIN_REQUEST

    def __init__(self, request_id, role, flags):
        super(FCGIBeginRequest, self).__init__(request_id)
        self.role = role
        self.flags = flags

    def encode(self):
        content = self.struct.pack(self.role, self.flags)
        return self.encode_header(content) + content


class FCGIAbortRequest(FCGIRecord):
    __slots__ = ()

    record_type = FCGI_ABORT_REQUEST

    @classmethod
    def parse(cls, request_id, content):
        return cls(request_id)

    def encode(self):
        return self.encode_header(b'')


class FCGIParams(FCGIBytestreamRecord):
    __slots__ = ()

    record_type = FCGI_PARAMS


class FCGIStdin(FCGIBytestreamRecord):
    __slots__ = ()

    record_type = FCGI_STDIN


class FCGIStdout(FCGIBytestreamRecord):
    __slots__ = ()

    record_type = FCGI_STDOUT


class FCGIStderr(FCGIBytestreamRecord):
    __slots__ = ()

    record_type = FCGI_STDERR


class FCGIData(FCGIBytestreamRecord):
    __slots__ = ()

    record_type = FCGI_DATA


class FCGIEndRequest(FCGIRecord):
    __slots__ = ('app_status', 'protocol_status')

    struct = Struct('>IB3x')
    record_type = FCGI_END_REQUEST

    def __init__(self, request_id, app_status, protocol_status):
        super(FCGIEndRequest, self).__init__(request_id)
        self.app_status = app_status
        self.protocol_status = protocol_status

    def encode(self):
        content = self.struct.pack(self.app_status, self.protocol_status)
        return self.encode_header(content) + content

record_classes = {cls.record_type: cls for cls in globals().values()  # type: ignore
                  if isinstance(cls, type) and issubclass(cls, FCGIRecord)
                  and cls.record_type}  # type: ignore


def decode_name_value_pairs(buffer):
    """
    Decode a name-value pair list from a buffer.

    :param bytearray buffer: a buffer containing a FastCGI name-value pair list
    :raise ProtocolError: if the buffer contains incomplete data
    :return: a list of (name, value) tuples where both elements are unicode strings
    :rtype: list

    """
    index = 0
    pairs = []
    while index < len(buffer):
        if buffer[index] & 0x80 == 0:
            name_length = buffer[index]
            index += 1
        elif len(buffer) - index > 4:
            name_length = length4_struct.unpack_from(buffer, index)[0] & 0x7fffffff
            index += 4
        else:
            raise ProtocolError('not enough data to decode name length in name-value pair')

        if len(buffer) - index > 1 and buffer[index] & 0x80 == 0:
            value_length = buffer[index]
            index += 1
        elif len(buffer) - index > 4:
            value_length = length4_struct.unpack_from(buffer, index)[0] & 0x7fffffff
            index += 4
        else:
            raise ProtocolError('not enough data to decode value length in name-value pair')

        if len(buffer) - index >= name_length + value_length:
            name = buffer[index:index + name_length].decode('ascii')
            value = buffer[index + name_length:index + name_length + value_length].decode('utf-8')
            pairs.append((name, value))
            index += name_length + value_length
        else:
            raise ProtocolError('name/value data missing from buffer')

    return pairs


def encode_name_value_pairs(pairs):
    """
    Encode a list of name-pair values into a binary form that FCGI understands.

    Both names and values can be either unicode strings or bytestrings and will be converted to
    bytestrings as necessary.

    :param list pairs: list of name-value pairs
    :return: the encoded bytestring

    """
    content = bytearray()
    for name, value in pairs:
        name = name if isinstance(name, bytes) else name.encode('ascii')
        value = value if isinstance(value, bytes) else value.encode('ascii')
        for item in (name, value):
            if len(item) < 128:
                content.append(len(item))
            else:
                length = len(item)
                content.extend(length4_struct.pack(length | 0x80000000))

        content.extend(name)
        content.extend(value)

    return bytes(content)


def decode_record(buffer):
    """
    Create a new FCGI message from the bytes in the given buffer.

    If successful, the record's data is removed from the byte array.

    :param bytearray buffer: the byte array containing the data
    :return: an instance of this class, or ``None`` if there was not enough data

    """
    if len(buffer) >= headers_struct.size:
        version, record_type, request_id, content_length, padding_length = \
            headers_struct.unpack_from(buffer)
        if version != 1:
            raise ProtocolError('unexpected protocol version: %d' % buffer[0])
        elif len(buffer) >= headers_struct.size + content_length + padding_length:
            content = buffer[headers_struct.size:headers_struct.size + content_length]
            del buffer[:headers_struct.size + content_length + padding_length]
            try:
                record_class = record_classes[record_type]
            except KeyError:
                if request_id:
                    raise ProtocolError('unknown record type: %d' % record_type)
                else:
                    return FCGIUnknownManagementRecord(record_type)

            return record_class.parse(request_id, content)

    return None
