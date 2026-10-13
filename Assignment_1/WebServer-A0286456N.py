import socket
import sys
from dataclasses import dataclass, field

HEADER_TERMINATOR = b'  '
KEY_PREFIX = '/key/'
COUNTER_PREFIX = '/counter/'
RECEIVE_SIZE = 4096


@dataclass
class Request:
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b''


@dataclass
class Response:
    status_code: int
    status_description: str
    body: bytes = b''


class KeyValueStore:
    """Maintains values and the access counters for temporary values."""

    def __init__(self):
        self._values = {}  # type: Dict[str, bytes]
        self._counters = {}  # type: Dict[str, int]

    def contains(self, key):
        return key in self._values

    def is_temporary(self, key):
        return key in self._counters

    def set_value(self, key, value):
        if self.is_temporary(key):
            return False

        self._values[key] = value
        return True

    def get_value(self, key):
        value = self._values[key]

        if self.is_temporary(key):
            self._counters[key] -= 1
            if self._counters[key] <= 0:
                del self._counters[key]
                del self._values[key]

        return value

    def delete_value(self, key):
        return self._values.pop(key)

    def increment_counter(self, key, increment):
        self._counters[key] = self._counters.get(key, 0) + increment

    def get_counter(self, key):
        return self._counters[key]

    def delete_counter(self, key):
        return self._counters.pop(key)


def ok(body=b''):
    return Response(200, 'OK', body)


def not_found():
    return Response(404, 'NotFound')


def method_not_allowed():
    return Response(405, 'MethodNotAllowed')


def read_request(connection, buffer):
    """Read one complete request, preserving bytes for subsequent requests."""
    while HEADER_TERMINATOR not in buffer:
        chunk = connection.recv(RECEIVE_SIZE)
        if not chunk:
            return None
        buffer += chunk

    header_bytes, body_buffer = buffer.split(HEADER_TERMINATOR, 1)

    try:
        tokens = header_bytes.decode('ascii').split()
    except UnicodeDecodeError:
        return None

    if len(tokens) < 2:
        return None

    headers = {}
    for index in range(2, len(tokens) - 1, 2):
        headers[tokens[index].lower()] = tokens[index + 1]

    try:
        content_length = int(headers.get('content-length', '0'))
    except ValueError:
        return None

    if content_length < 0:
        return None

    while len(body_buffer) < content_length:
        chunk = connection.recv(RECEIVE_SIZE)
        if not chunk:
            return None
        body_buffer += chunk

    request = Request(
        method=tokens[0].upper(),
        path=tokens[1],
        headers=headers,
        body=body_buffer[:content_length],
    )
    remaining_buffer = body_buffer[content_length:]
    return request, remaining_buffer


def handle_key_request(request, store):
    key = request.path[len(KEY_PREFIX):]

    if request.method == 'POST':
        if not store.set_value(key, request.body):
            return method_not_allowed()
        return ok()

    if request.method == 'GET':
        if not store.contains(key):
            return not_found()
        return ok(store.get_value(key))

    if request.method == 'DELETE':
        if not store.contains(key):
            return not_found()
        if store.is_temporary(key):
            return method_not_allowed()
        return ok(store.delete_value(key))

    return not_found()


def handle_counter_request(request, store):
    key = request.path[len(COUNTER_PREFIX):]

    if request.method == 'POST':
        if not store.contains(key):
            return method_not_allowed()

        try:
            increment = int(request.body.decode('ascii'))
        except (UnicodeDecodeError, ValueError):
            increment = 0

        store.increment_counter(key, increment)
        return ok()

    if request.method == 'GET':
        if not store.contains(key):
            return not_found()

        if store.is_temporary(key):
            counter_text = str(store.get_counter(key))
        else:
            counter_text = 'Infinity'
        return ok(counter_text.encode('ascii'))

    if request.method == 'DELETE':
        if not store.is_temporary(key):
            return not_found()

        deleted_counter = str(store.delete_counter(key)).encode('ascii')
        return ok(deleted_counter)

    return not_found()


def handle_request(request, store):
    if request.path.startswith(KEY_PREFIX):
        return handle_key_request(request, store)

    if request.path.startswith(COUNTER_PREFIX):
        return handle_counter_request(request, store)

    return not_found()


def encode_response(response):
    """Serialize a response using the assignment protocol."""
    header = f'{response.status_code} {response.status_description}'
    if response.body:
        header += f' Content-Length {len(response.body)}'

    return header.encode('ascii') + HEADER_TERMINATOR + response.body


def serve_connection(connection, store):
    buffer = b''

    while True:
        parsed_request = read_request(connection, buffer)
        if parsed_request is None:
            return

        request, buffer = parsed_request
        response = handle_request(request, store)
        connection.sendall(encode_response(response))


def run_server(port):
    store = KeyValueStore()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', port))
        server_socket.listen(5)

        while True:
            connection, _ = server_socket.accept()
            with connection:
                serve_connection(connection, store)


def parse_port(arguments):
    if len(arguments) < 2:
        raise ValueError('Missing port number')
    return int(arguments[1])


def main():
    try:
        port = parse_port(sys.argv)
    except ValueError:
        sys.exit(1)

    run_server(port)


if __name__ == '__main__':
    main()
