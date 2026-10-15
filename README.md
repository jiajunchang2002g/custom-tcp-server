# TCP key-value server

The server uses a custom protocol, **not HTTP**. It supports binary data, persistent connections, and temporary values that expire after a configured number of reads.

<img width="2553" height="1510" alt="image" src="https://github.com/user-attachments/assets/9c0ad31a-c803-4fc3-81a5-a66f581c7e22" />

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

The program buffers partial packets and flushes each complete payload immediately.

Example:

```python
python3 PacketExtr.py < test.in > test.out
```

## Testing

## Limitations

- Storage is in memory only.
- Clients are served sequentially so an idle client can block other clients.
- The server has no per-connection timeout or request-size limits.
- There is no authentication or TLS.
