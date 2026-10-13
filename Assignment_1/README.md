# CS2105 Assignment 1 — Key-Value Server

This project implements a TCP key-value server and a command-line client for the assignment's space-delimited protocol.

## Files

- `WebServer-A0286456N.py` — persistent TCP server and in-memory data store
- `Client-A0286456N.py` — command-line client for sending one request
- `test/` — supplied test scripts
- `*.so` — supplied Linux test modules

Both Python programs use only the Python standard library.

## Requirements

- Python 3.8 or newer
- A free local TCP port

## Start the server

Run the server with a port number:

```sh
python3 WebServer-A0286456N.py 8080
```

The server listens on all local interfaces and processes clients sequentially. Values and counters are held in memory and are lost when the server stops.

## Use the client

The client syntax is:

```text
python3 Client-A0286456N.py HOST PORT METHOD PATH [BODY] [--body-file FILE]
```

`METHOD` can be `GET`, `POST`, or `DELETE`. Method input is case-insensitive.

### Store a value

```sh
python3 Client-A0286456N.py localhost 8080 POST /key/name Alice
```

Expected response:

```text
200 OK
```

### Retrieve a value

```sh
python3 Client-A0286456N.py localhost 8080 GET /key/name
```

Expected response:

```text
200 OK
Alice
```

### Delete a value

```sh
python3 Client-A0286456N.py localhost 8080 DELETE /key/name
```

The deleted value is returned in the response body.

### Send a file as the value

```sh
python3 Client-A0286456N.py localhost 8080 POST /key/document --body-file example.txt
```

`--body-file` preserves the file's raw bytes. It cannot be combined with the positional `BODY` argument.

### Configure the timeout

The client waits up to five seconds by default. Use `--timeout` to change it:

```sh
python3 Client-A0286456N.py localhost 8080 GET /key/name --timeout 10
```

## Counter behavior

A counter makes an existing key temporary. Each successful `GET /key/<key>` decrements its counter; the key and counter are removed when the counter reaches zero.

Create a value and assign two reads:

```sh
python3 Client-A0286456N.py localhost 8080 POST /key/token secret
python3 Client-A0286456N.py localhost 8080 POST /counter/token 2
```

Inspect the remaining count:

```sh
python3 Client-A0286456N.py localhost 8080 GET /counter/token
```

A permanent key has an `Infinity` counter. Removing a finite counter makes its associated key permanent again:

```sh
python3 Client-A0286456N.py localhost 8080 DELETE /counter/token
```

Temporary values cannot be overwritten or directly deleted while their counters exist.

## Protocol summary

Requests use this format:

```text
METHOD PATH [Content-Length LENGTH]  BODY
```

Responses use this format:

```text
STATUS_CODE STATUS_DESCRIPTION [Content-Length LENGTH]  BODY
```

Two spaces terminate the header. A body may contain arbitrary bytes and is framed using `Content-Length`. The server supports multiple requests on one persistent connection, including requests received together in one TCP packet.

### Routes

| Route | Method | Behavior |
|---|---|---|
| `/key/<key>` | `POST` | Create or replace a permanent value |
| `/key/<key>` | `GET` | Return a value and consume one finite read |
| `/key/<key>` | `DELETE` | Delete and return a permanent value |
| `/counter/<key>` | `POST` | Add the body integer to an existing key's counter |
| `/counter/<key>` | `GET` | Return the finite counter or `Infinity` |
| `/counter/<key>` | `DELETE` | Delete and return a finite counter |

### Status codes

| Status | Meaning |
|---|---|
| `200 OK` | The operation succeeded |
| `404 NotFound` | The route, key, or finite counter does not exist |
| `405 MethodNotAllowed` | The operation conflicts with the key/counter state |

## Testing

On the Linux environment expected by the supplied binaries, run:

```sh
bash test/WebServer.sh
```

The supplied `*.so` test modules are Linux x86-64 ELF binaries, so the complete harness cannot run natively on macOS.
