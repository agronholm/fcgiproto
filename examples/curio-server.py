from curio import run, spawn
from curio.socket import *

from fcgiproto import FastCGIConnection, RequestBeginEvent, RequestDataEvent


async def fcgi_server(address):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    async with sock:
        while True:
            client, addr = await sock.accept()
            await spawn(fcgi_client(client, addr))


def handle_request(conn, request_id, params, content):
    fcgi_params = '\n'.join('<tr><td>%s</td><td>%s</td></tr>' % (key, value)
                            for key, value in params.items())
    content = content.decode('utf-8', errors='replace')
    response = ("""\
<!DOCTYPE html>
<html>
<body>
<h2>FCGI parameters</h2>
<table>
%s
</table>
<h2>Request body</h2>
<pre>%s</pre>
</body>
</html>
""" % (fcgi_params, content)).encode('utf-8')
    headers = [
        (b'Content-Length', str(len(response)).encode('ascii')),
        (b'Content-Type', b'text/html; charset=UTF-8')
    ]
    conn.send_headers(request_id, headers, 200)
    conn.send_data(request_id, response, end_request=True)


async def fcgi_client(client, addr):
    conn = FastCGIConnection()
    requests = {}
    async with client:
        while True:
            data = await client.recv(100000)
            if not data:
                break

            for event in conn.feed_data(data):
                if isinstance(event, RequestBeginEvent):
                    requests[event.request_id] = (
                        event.params, event.keep_connection, bytearray())
                elif isinstance(event, RequestDataEvent):
                    request_data = requests[event.request_id][2]
                    if event.data:
                        request_data.extend(event.data)
                    else:
                        params, keep_connection, request_data = requests.pop(event.request_id)
                        handle_request(conn, event.request_id, params, request_data)
                        if not keep_connection:
                            break

            data = conn.data_to_send()
            if data:
                await client.sendall(data)

if __name__ == '__main__':
    try:
        run(fcgi_server(('', 9500)))
    except (KeyboardInterrupt, SystemExit):
        pass
