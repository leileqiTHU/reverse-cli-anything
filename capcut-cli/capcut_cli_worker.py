"""Disposable, version-pinned native host. Invoked only by capcut_agent.py."""
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import sys

PINS = {
    "lyra_cli_client.dll": "1760a1d8752c2cba1c3ea572f3c1ec0ce4e8ca0da90b0bb8032d297804bcde97",
    "videoeditor.dll": "029986c9a26f3db4222402d00283cc610c81247b50ee9827e281daf626426b90",
}
HELP_TOPICS = {"root": "", "media": "media", "probe": "media probe", "convert-image": "media transcode-image"}


def quoted_path(value):
    # The DLL's tokenizer accepts quoted forward-slash Windows paths.
    value = str(Path(value).resolve()).replace("\\", "/")
    if any(ch in value for ch in ('"', "\n", "\r", "\0")):
        raise ValueError("Path contains unsupported command-token characters")
    return '"' + value + '"'


def command_for(req):
    op = req["operation"]
    if op == "version":
        return "--version"
    if op == "help":
        return (HELP_TOPICS[req["topic"]] + " --help").strip()
    if op == "probe":
        return "media probe --input " + quoted_path(req["input"])
    if op == "convert-image":
        if req["format"] not in ("jpg", "jpeg", "png"):
            raise ValueError("Unsupported image format")
        if Path(req["output"]).exists():
            raise ValueError("Worker output already exists")
        return ("media transcode-image --input " + quoted_path(req["input"])
                + " --output " + quoted_path(req["output"]) + " --format " + req["format"])
    raise ValueError("Operation is not allowed")


def execute(req):
    base = Path(req["capcut_dir"])
    for name, expected in PINS.items():
        with (base / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Unsupported DLL build: {name} SHA256 {actual}")
    command = command_for(req)
    # Suppress Windows fault dialogs in this isolated process.
    c.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    directory = os.add_dll_directory(str(base))
    dll = c.WinDLL(str(base / "lyra_cli_client.dll"))
    create = getattr(dll, "?Create@Client@lyra_cli@@SA?AV?$shared_ptr@VClient@lyra_cli@@@std@@J@Z")
    create.argtypes, create.restype = [c.c_void_p, c.c_int], c.c_void_p
    shared = (c.c_void_p * 2)()
    create(shared, 1)
    obj, control = shared[:]
    vt = c.c_void_p.from_address(obj).value
    if vt - dll._handle != 0x6225a8:
        raise ValueError("Unexpected ClientImpl vtable")
    run = c.CFUNCTYPE(c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p)(
        c.c_void_p.from_address(vt + 16).value)
    data = command.encode("utf8")
    backing = c.create_string_buffer(data)
    arg = c.create_string_buffer(32)
    if len(data) < 16:
        c.memmove(c.addressof(arg), data, len(data))
    else:
        c.c_void_p.from_buffer(arg).value = c.addressof(backing)
    c.c_uint64.from_buffer(arg, 16).value = len(data)
    c.c_uint64.from_buffer(arg, 24).value = max(15, len(data))
    result = c.create_string_buffer(104)
    options = c.create_string_buffer(32)
    c.c_int.from_buffer(options).value = -1
    sentinel = c.create_string_buffer(0x60)
    for offset in (0, 8, 16):
        c.c_void_p.from_buffer(sentinel, offset).value = c.addressof(sentinel)
    c.c_uint16.from_buffer(sentinel, 24).value = 0x0101
    c.c_void_p.from_buffer(options, 8).value = c.addressof(sentinel)
    c.c_ubyte.from_buffer(options, 24).value = 1

    def string_at(offset):
        address = c.addressof(result) + offset
        size = c.c_uint64.from_address(address + 16).value
        capacity = c.c_uint64.from_address(address + 24).value
        if size > 4 * 1024 * 1024 or capacity < size:
            raise ValueError("Invalid native result string")
        pointer = address if capacity < 16 else c.c_void_p.from_address(address).value
        return c.string_at(pointer, size).decode("utf8", errors="replace")

    run(obj, result, arg, options)
    report = {"exitCode": c.c_int.from_buffer(result).value,
              "stdout": string_at(8), "stderr": string_at(40), "metadata": string_at(72)}
    c.CFUNCTYPE(None, c.c_void_p)(dll._handle + 0x15b30)(result)
    c.CFUNCTYPE(None, c.c_void_p)(dll._handle + 0x193a0)(control)
    return report


if __name__ == "__main__":
    request_path, response_path = map(Path, sys.argv[1:3])
    try:
        report = execute(json.loads(request_path.read_text(encoding="utf8")))
    except Exception as error:
        report = {"workerError": str(error)}
    response_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf8")
