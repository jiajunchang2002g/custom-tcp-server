import sys


def main():
    buffer = b""

    while True:
        chunk = sys.stdin.buffer.read1(4096)

        # EOF detection
        if not chunk and not buffer:
            break

        buffer += chunk

        # 2. Process all complete packets currently sitting in the buffer
        while True:
            # We look for the end of the header marker 'B' completely in binary
            header_end = buffer.find(b'B')
            if header_end == -1:
                # Header is incomplete; exit inner loop to read more data
                break

            # Extract the header slice
            header_bytes = buffer[:header_end + 1]

            # Safely decode ONLY the ASCII header slice to extract the size
            try:
                header_str = header_bytes.decode('ascii')
                # Format is "Size: <size>B"
                size_str = header_str.split(' ')[1][:-1]
                payload_size = int(size_str)
            except (IndexError, ValueError):
                # Fallback safeguard (assignment says formats are guaranteed correct)
                break

            # Calculate total expected size of this packet (header + payload)
            total_packet_size = (header_end + 1) + payload_size

            # Check if the full payload has arrived in the buffer yet
            if len(buffer) < total_packet_size:
                # Payload is incomplete; exit inner loop to read more data
                break

            # 3. Extract the payload using binary slicing
            payload_start = header_end + 1
            payload = buffer[payload_start:total_packet_size]

            # 4. Immediate, responsive output to stdout
            sys.stdout.buffer.write(payload)
            sys.stdout.buffer.flush()

            # Remove the processed packet from the buffer and repeat
            buffer = buffer[total_packet_size:]

if __name__ == '__main__':
    main()
