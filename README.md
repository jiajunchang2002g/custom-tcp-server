# TCP key-value server

A collection of small Python networking utilities centered on a TCP key-value server and its command-line client.

The server uses a custom protocol, **not HTTP**. It supports binary data, persistent connections, and temporary values that expire after a configured number of reads.


## Files

| File | Description |
|---|---|
| `WebServer.py` | TCP key-value server with in-memory storage |
| `Client.py` | Command-line client for sending one request |
| `PacketExtr.py` | Extracts payloads from a framed byte stream |
| `Checksum.py` | Calculates a file’s CRC32 checksum |

## Quick Start

Run these commands from the project directory.

Start the server:

```sh
python3 WebServer.py 8080
```

In another terminal, store and retrieve a value:

```sh
python3 Client.py localhost 8080 POST /key/name Alice
python3 Client.py localhost 8080 GET /key/name
```

Expected retrieval output:

```text
200 OK
Alice
```

Stop the server with `Ctrl+C`.

> The server listens on all local interfaces. All values and counters are held in memory and are lost when the server stops.

## Command-Line Client

```text
python3 Client.py HOST PORT METHOD PATH [BODY] [--body-file FILE] [--timeout SECONDS]
```

- `METHOD`: `GET`, `POST`, or `DELETE`; case-insensitive.
- `PATH`: `/key/<key>` or `/counter/<key>`.
- `BODY`: optional text, encoded as UTF-8.
- `--body-file`: reads the request body as raw bytes from a file.
- `--timeout`: socket timeout in seconds; defaults to `5`.

`BODY` and `--body-file` cannot be used together. Paths must be ASCII and must not contain whitespace.

### Store or Replace a Value

```sh
python3 Client.py localhost 8080 POST /key/greeting "Hello, world!"
```

### Retrieve a Value

```sh
python3 Client.py localhost 8080 GET /key/greeting
```

### Delete a Value

```sh
python3 Client.py localhost 8080 DELETE /key/greeting
```

A successful deletion returns the deleted value.

### Upload a File

```sh
python3 Client.py localhost 8080 POST /key/document --body-file README.md
```

File contents are transmitted without text encoding or conversion.

The client prints a status line followed by the response body, if present, and a newline. Its output is therefore not a raw-body download format.

### Change the Timeout

```sh
python3 Client.py localhost 8080 GET /key/document --timeout 10
```

## Temporary Values and Counters

Keys are permanent by default. Assigning a counter limits how many times a value can be retrieved.

```sh
# Store a value
python3 Client.py localhost 8080 POST /key/token secret

# Allow two successful reads
python3 Client.py localhost 8080 POST /counter/token 2

# Inspect the remaining reads without consuming one
python3 Client.py localhost 8080 GET /counter/token

# Consume the first read
python3 Client.py localhost 8080 GET /key/token

# Consume the final read, removing the value and counter
python3 Client.py localhost 8080 GET /key/token

# The value no longer exists
python3 Client.py localhost 8080 GET /key/token
```

Counter behavior:

- Posting a counter requires an existing key.
- Posting again adds the supplied integer to the current counter.
- Each successful key `GET` decrements its counter.
- The final permitted read returns the value before removing it.
- Temporary values cannot be overwritten or directly deleted.
- A permanent key’s counter is reported as `Infinity`.
- Deleting a finite counter returns its previous count and makes the key permanent again.

To remove a read limit:

```sh
python3 Client.py localhost 8080 DELETE /counter/token
```

Use positive integers for counter updates. The current implementation does not reject zero, negative, or malformed counter bodies.

## Protocol

This is a custom protocol over TCP. It does not use HTTP headers or line endings.

### Request Format

```text
METHOD PATH [Content-Length LENGTH]  BODY
```

### Response Format

```text
STATUS_CODE STATUS_DESCRIPTION [Content-Length LENGTH]  BODY
```

Rules:

- Exactly two consecutive spaces mark the end of the header.
- Header text is ASCII.
- `Content-Length` specifies the body length in bytes.
- Bodies may contain arbitrary bytes, including spaces.
- An omitted `Content-Length` means a zero-length body.
- Methods and header names are handled case-insensitively.

Example request and response:

```text
POST /key/name Content-Length 5  Alice
200 OK  
```

The response above ends with two spaces and has no body.

A subsequent retrieval:

```text
GET /key/name  
200 OK Content-Length 5  Alice
```

The server supports multiple requests per connection and buffers partial requests and bytes belonging to subsequent requests. The command-line client opens a new connection for each invocation.

### Routes

| Route | Method | Behavior |
|---|---|---|
| `/key/<key>` | `POST` | Create or replace a permanent value |
| `/key/<key>` | `GET` | Return a value and consume one finite read |
| `/key/<key>` | `DELETE` | Delete and return a permanent value |
| `/counter/<key>` | `POST` | Add an integer to an existing key’s counter |
| `/counter/<key>` | `GET` | Return the remaining count or `Infinity` |
| `/counter/<key>` | `DELETE` | Remove and return a finite counter |

### Status Codes

| Status | Meaning |
|---|---|
| `200 OK` | Operation succeeded |
| `404 NotFound` | Route, key, or requested finite counter does not exist |
| `405 MethodNotAllowed` | Operation conflicts with the current key/counter state |

## Packet Extractor

`PacketExtr.py` reads a binary stream from standard input. Each packet uses this format:

```text
Size: <length>B<payload>
```

`<length>` is the payload size in bytes. The script removes packet headers and writes concatenated payloads to standard output.

Example:

```sh
printf 'Size: 5BHelloSize: 6B world' | python3 PacketExtr.py
```

Output:

```text
Hello world
```

The extractor buffers partial packets and flushes each complete payload immediately.

**Current limitation:** input must contain complete, correctly formatted packets. EOF with an incomplete packet can cause the script to loop indefinitely.

```sh
python3 Checksum.py README.md
```

The script reads the entire file as bytes and prints its CRC32 checksum as a decimal integer.

## Testing

For a manual smoke test:

1. Start the server.
2. Store a value and verify that retrieval returns it.
3. Replace the value and verify the updated contents.
4. Delete it and verify that another retrieval returns `404 NotFound`.
5. Store another value and assign a counter of `2`.
6. Verify that two reads succeed and the third returns `404 NotFound`.
7. Verify that overwriting or deleting a temporary value returns `405 MethodNotAllowed`.


## Limitations

- Storage is in memory only.
- Clients are served sequentially so an idle client can block other clients.
- The server has no per-connection timeout or request-size limits.
- There is no authentication or TLS.
