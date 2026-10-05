"""Cancellable process output, with a PTY to avoid stdio buffering."""
import codecs
import errno
import fcntl
import struct
import termios
import os
import pty
import selectors
import signal
import subprocess
import time
import tty


def signal_group(process, sig):
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def stream_process(args, cancelled, on_line, *, use_pty=True):
    master = slave = None
    process = None
    try:
        # No terminal echo or newline transformations. The child sees a terminal
        # for line buffering; paths containing literal CR/LF are not submitted.
        if use_pty:
            master, slave = pty.openpty()
            tty.setraw(slave)
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 120, 0, 0))
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                   stdout=slave if use_pty else subprocess.PIPE,
                                   stderr=slave if use_pty else subprocess.STDOUT,
                                   start_new_session=True, env={**os.environ, "LC_ALL": "C"})
        if slave is not None:
            os.close(slave)
            slave = None
        if not use_pty:
            master = process.stdout.fileno()
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        pending = ""
        terminated = None
        with selectors.DefaultSelector() as selector:
            selector.register(master, selectors.EVENT_READ)
            while selector.get_map() or process.poll() is None:
                if cancelled.is_set():
                    if terminated is None:
                        signal_group(process, signal.SIGTERM)
                        terminated = time.monotonic()
                    elif time.monotonic() - terminated > 2:
                        signal_group(process, signal.SIGKILL)
                for key, _ in selector.select(timeout=.1):
                    try:
                        chunk = os.read(key.fd, 8192)
                    except OSError as exc:
                        if exc.errno != errno.EIO:
                            raise
                        chunk = b""
                    if not chunk:
                        selector.unregister(key.fd)
                        pending += decoder.decode(b"", final=True)
                        continue
                    pending += decoder.decode(chunk)
                    # freshclam uses carriage returns for its download indicator.
                    pending = pending.replace("\r", "\n")
                    while "\n" in pending:
                        line, pending = pending.split("\n", 1)
                        if line:
                            on_line(line)
                    if len(pending) > 16384:
                        on_line(pending[:4096] + " [длинная строка сокращена]")
                        pending = ""
                if not selector.get_map() and process.poll() is None:
                    cancelled.wait(.05)
            if pending:
                on_line(pending)
        return process.wait()
    finally:
        if process:
            if process.poll() is None:
                signal_group(process, signal.SIGKILL)
            process.wait()
        if slave is not None:
            os.close(slave)
        if not use_pty and process is not None:
            process.stdout.close()
        elif master is not None:
            os.close(master)
