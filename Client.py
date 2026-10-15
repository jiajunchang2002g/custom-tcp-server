import argparse
import socket
import sys
from dataclasses import dataclass, field

HEADER_TERMINATOR = b'  '
RECEIVE_SIZE = 4096


@dataclass
class Response:
    status_code: int
    status_description: str
    headers: dict = field(default_factory=dict)
    body: bytes = b''


def encode_request(method, path, body):
    header = f'{method.upper()} {path}'
    if body:
        header += f' Content-Length {len(body)}'
    return header.encode('ascii') + HEADER_TERMINATOR + body


def receive_response(connection):
    buffer = b''
    while HEADER_TERMINATOR not in buffer:
        chunk = connection.recv(RECEIVE_SIZE)
        if not chunk:
            raise ConnectionError('Server closed the connection before sending a response')
        buffer += chunk

    header_bytes, body_buffer = buffer.split(HEADER_TERMINATOR, 1)
    try:
        tokens = header_bytes.decode('ascii').split()
    except UnicodeDecodeError as error:
        raise ValueError('Response header is not valid ASCII') from error

    if len(tokens) < 2:
        raise ValueError('Response header is incomplete')

    headers = {}
    for index in range(2, len(tokens) - 1, 2):
        headers[tokens[index].lower()] = tokens[index + 1]

    try:
        content_length = int(headers.get('content-length', '0'))
    except ValueError as error:
        raise ValueError('Response has an invalid Content-Length') from error

    if content_length < 0:
        raise ValueError('Response has a negative Content-Length')

    while len(body_buffer) < content_length:
        chunk = connection.recv(RECEIVE_SIZE)
        if not chunk:
            raise ConnectionError('Server closed the connection before sending the full body')
        body_buffer += chunk

    try:
        status_code = int(tokens[0])
    except ValueError as error:
        raise ValueError('Response has an invalid status code') from error

    return Response(
        status_code=status_code,
        status_description=tokens[1],
        headers=headers,
        body=body_buffer[:content_length],
    )


def send_request(host, port, method, path, body, timeout):
    request = encode_request(method, path, body)
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.sendall(request)
        return receive_response(connection)


def read_body(arguments, parser):
    if arguments.body is not None and arguments.body_file is not None:
        parser.error('body and --body-file cannot be used together')

    if arguments.body_file is not None:
        with open(arguments.body_file, 'rb') as body_file:
            return body_file.read()

    if arguments.body is not None:
        return arguments.body.encode('utf-8')

    return b''


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description='Send one request to the assignment key-value server.',
    )
    parser.add_argument('host', help='server hostname or IP address')
    parser.add_argument('port', type=int, help='server TCP port')
    parser.add_argument('method', choices=('GET', 'POST', 'DELETE'), type=str.upper)
    parser.add_argument('path', help='request path, such as /key/name')
    parser.add_argument('body', nargs='?', help='optional UTF-8 request body')
    parser.add_argument('--body-file', help='read the request body as bytes from a file')
    parser.add_argument(
        '--timeout',
        type=float,
        default=5.0,
        help='socket timeout in seconds (default: 5)',
    )
    return parser


def print_response(response):
    output = (
        f'{response.status_code} {response.status_description}\n'
    ).encode('ascii')
    if response.body:
        output += response.body + b'\n'
    sys.stdout.buffer.write(output)


def main():
    parser = create_argument_parser()
    arguments = parser.parse_args()

    if not 0 <= arguments.port <= 65535:
        parser.error('port must be between 0 and 65535')
    if arguments.timeout <= 0:
        parser.error('--timeout must be positive')

    try:
        body = read_body(arguments, parser)
        response = send_request(
            arguments.host,
            arguments.port,
            arguments.method,
            arguments.path,
            body,
            arguments.timeout,
        )
    except (OSError, ConnectionError, ValueError) as error:
        print(f'Client error: {error}', file=sys.stderr)
        sys.exit(1)

    print_response(response)


if __name__ == '__main__':
    main()
