Protocol implementor's guide
============================

Creating a real-world implementation of FastCGI using fcgiproto is quite straightforward.
As with other sans-io protocols, you feed incoming data to fcgiproto and it vends events in return.
To invoke actions on the connection, just call its methods, like
:meth:`~fcgiproto.FastCGIConnection.send_headers` and so on.
To get pending outgoing data, use the :meth:`~fcgiproto.FastCGIConnection.data_to_send` method.

Connection configuration
------------------------

The most common role is the responder role (``FCGI_RESPONDER``). The authorizer
(``FCGI_AUTHORIZER``) and filter (``FCGI_FILTER``) roles are not commonly supported by web server
software. As such, you will want to leave the default role setting alone, unless you really know
what you're doing.

It's also possible to set FCGI management values. The FastCGI specification defines names of three
values:

* ``FCGI_MAX_CONNS``: The maximum number of concurrent transport connections this application will
  accept, e.g. ``1`` or ``10``
* ``FCGI_MAX_REQS``: The maximum number of concurrent requests this application will accept, e.g.
  ``1`` or ``50``.
* ``FCGI_MPXS_CONNS``: ``0`` if this application does not multiplex connections (i.e. handle
  concurrent requests over each connection), ``1`` otherwise.

The connection sets ``FCGI_MPXS_CONNS`` to ``1`` by default. It should be noted that the web server
may never even query for these values, so leave this setting alone unless you know you need it.
At least nginx does not attempt to multiplex FCGI connections, nor does it query for any management
values.

Implementor's responsibilities
------------------------------

The logic in :class:`~fcgiproto.FastCGIConnection` will handle most complications of the protocol.
That leaves just a handful of things for I/O implementors to keep in mind:

* Always get any outgoing data from the connection (using
  :meth:`~fcgiproto.FastCGIConnection.data_to_send`) after calling either
  :meth:`~fcgiproto.FastCGIConnection.feed_data` or any of the other methods, and send it to the
  remote host
* Remember to set ``Content-Length`` if your response contains a body
* Respect the ``keep_connection`` flag in :class:`~fcgiproto.RequestBeginEvent`.
  Close the connection after calling :meth:`~fcgiproto.FastCGIConnection.end_request` if the flag
  is ``False``.

Handling requests
-----------------

**RESPONDER**

The sequence for handling responder requests (the most common case) is as follows:

#. a :class:`~fcgiproto.RequestBeginEvent` is received
#. one or more :class:`~fcgiproto.RequestDataEvent` are received, the last one having an empty
   bytestring as ``data`` attribute
#. the application calls :meth:`~fcgiproto.FastCGIConnection.send_headers` once
#. the application calls :meth:`~fcgiproto.FastCGIConnection.send_data` one or more times
   and the last call must have ``end_request`` set to ``True``

The implementor can decide whether to wait until all of the request body has been received, or
start running the request handler code right after :class:`~fcgiproto.RequestBeginEvent` has been
received (to facilitate streaming uploads for example).

In FastCGI responses, the HTTP status code is sent using the ``Status`` header. As a convenience,
the :meth:`~fcgiproto.FastCGIConnection.send_headers` method provides the ``status`` parameter
to add this header.

**AUTHORIZER**

Authorizer requests differ from responder requests in the way that the application never receives
any request body. They also don't receive the ``CONTENT_LENGTH``, ``PATH_INFO``, ``SCRIPT_NAME`` or
``PATH_TRANSLATED`` parameters, which severely limits the usefulness of this role.

The request-response sequence for authorizers goes as follows:

#. a :class:`~fcgiproto.RequestBeginEvent` is received
#. the application calls :meth:`~fcgiproto.FastCGIConnection.send_headers` once
#. the application calls :meth:`~fcgiproto.FastCGIConnection.send_data` one or more times
   and the last call must have ``end_request`` set to ``True``

A response code other than ``200`` will be interpreted as a negative response.

**FILTER**

Filter applications receive all the same information as responders, but they are also sent a
secondary data stream which they're supposed to filter.

The request-response sequence for filters goes as follows:

#. a :class:`~fcgiproto.RequestBeginEvent` is received
#. one or more :class:`~fcgiproto.RequestDataEvent` are received, the last one having an empty
   bytestring as ``data`` attribute
#. one or more :class:`~fcgiproto.RequestSecondaryDataEvent` are received, the last one having an
   empty bytestring as ``data`` attribute
#. the application calls :meth:`~fcgiproto.FastCGIConnection.send_headers` once
#. the application calls :meth:`~fcgiproto.FastCGIConnection.send_data` one or more times
   and the last call must have ``end_request`` set to ``True``

The application is expected to send the (modified) secondary data stream as the response body.
It must read in all of the request body before starting to send a response (thus somewhat deviating
from the sequence above), but it does not need to wait for the secondary data stream to end (for
example if the response comes from a cache).

Handling request aborts
-----------------------

If the application receives a :class:`~fcgiproto.RequestAbortEvent`, it should cease processing of
the request at once. No headers or data should be sent from this point on for this request, and
:meth:`~fcgiproto.FastCGIConnection.end_request` should be called as soon as possible.

Running the examples
--------------------

The ``examples`` directory in the project source tree contains example code for several popular
I/O frameworks to get you started. Just run any of the server scripts and it will start a FastCGI
server listening on port 9500.

Since FastCGI requires a front-end server, a Docker script and configuration files for both nginx
and Apache HTTPd have been provided as a convenience. Just run either ``nginx_docker.sh`` or
``apache_docker.sh`` from the ``examples`` directory and navigate to http://127.0.0.1/ to see the
result. The example code displays a web page that shows the FastCGI parameters and the request body
(if any).

.. note:: You may have to make adjustments to the configuration if your Docker interface address or
    desired host HTTP port don't match the provided configuration.
