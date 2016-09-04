.. image:: https://travis-ci.org/agronholm/fcgiproto.svg?branch=master
  :target: https://travis-ci.org/agronholm/fcgiproto
  :alt: Build Status
.. image:: https://coveralls.io/repos/github/agronholm/fcgiproto/badge.svg?branch=master
  :target: https://coveralls.io/github/agronholm/fcgiproto?branch=master
  :alt: Code Coverage

The FastCGI_ protocol is a protocol commonly used to relay HTTP requests and responses between a
front-end web server (nginx, Apache, etc.) and a back-end web application.

This library implements this protocol for the web application end as a pure state-machine which
only takes in bytes and returns a list of parsed events. This leaves users free to use any I/O
approach they see fit (asyncio_, curio_, Twisted_, etc.). Sample code is provided for implementing
a FastCGI server using a variety of I/O frameworks.

.. _FastCGI: https://htmlpreview.github.io/?https://github.com/FastCGI-Archives/FastCGI.com/blob/master/docs/FastCGI%20Specification.html
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _curio: https://github.com/dabeaz/curio
.. _Twisted: https://twistedmatrix.com/

Project links
-------------

* `Documentation <http://fcgiproto.readthedocs.org/en/latest/>`_
* `Source code <https://github.com/agronholm/fcgiproto>`_
* `Issue tracker <https://github.com/agronholm/fcgiproto/issues>`_
