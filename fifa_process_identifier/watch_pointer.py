"""
Observa ao vivo o conteúdo apontado por uma cadeia de ponteiros do
tipo: fifa16.exe + <offset> -> [ponteiro] -> string (lida como bytes
próximo ao endereço apontado).

Isso é só leitura (ReadProcessMemory) — não escreve nada, não usa
breakpoints, não deve interferir no jogo/mod.

Uso:
    python watch_pointer.py <offset_hex> [read_size]

Exemplo:
    python watch_pointer.py 0x3357378 128
"""

from __future__ import annotations

import ctypes
import re
import sys
import time

import memory
import modules
import process

_PRINTABLE_RE = re.compile(rb"[ -~]{4,}")


def extract_strings(data: bytes) -> list[str]:
    return [m.group().decode("latin1") for m in _PRINTABLE_RE.finditer(data)]


def read_bytes_at(handle, address: int, size: int) -> bytes | None:
    buffer = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)

    ok = memory.ReadProcessMemory(
        handle,
        ctypes.c_void_p(address),
        buffer,
        size,
        ctypes.byref(bytes_read),
    )

    if not ok:
        return None

    return buffer.raw[: bytes_read.value]


def read_pointer(handle, address: int) -> int | None:
    raw = read_bytes_at(handle, address, 8)
    if raw is None or len(raw) < 8:
        return None
    return int.from_bytes(raw, "little")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python watch_pointer.py <offset_hex> [read_size]")
        sys.exit(1)

    offset = int(sys.argv[1], 16)
    read_size = int(sys.argv[2]) if len(sys.argv) > 2 else 96

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)
    mod_list = modules.list_modules(handle)

    exe_module = next(
        (m for m in mod_list if m.name.lower().endswith("fifa16.exe")), None
    )

    if exe_module is None:
        print("[ERROR] Não encontrei fifa16.exe entre os módulos.")
        sys.exit(1)

    base_address = exe_module.base + offset

    print(f"[INFO] fifa16.exe base = 0x{exe_module.base:012X}")
    print(f"[INFO] Endereço observado = 0x{base_address:012X} "
          f"(fifa16.exe+0x{offset:X})")
    print("[INFO] Pressione Ctrl+C para parar.")
    print()

    last_value = None
    last_bytes = None

    try:
        while True:
            ptr_value = read_pointer(handle, base_address)

            if ptr_value is None:
                print("[WARN] Falha ao ler o ponteiro (processo fechado?).")
                time.sleep(1)
                continue

            content = None
            if ptr_value != 0:
                content = read_bytes_at(handle, ptr_value, read_size)

            if ptr_value != last_value or content != last_bytes:
                timestamp = time.strftime("%H:%M:%S")
                strings_found = extract_strings(content) if content else []
                # prioriza strings que parecem nome de arquivo .swf
                # (identidade do widget/componente de UI ativo)
                swf_strings = [s for s in strings_found if ".swf" in s]
                label = swf_strings[0] if swf_strings else (strings_found[0] if strings_found else "(sem texto)")
                print(f"[{timestamp}] ponteiro=0x{ptr_value:012X}  ATIVO: {label}")

                last_value = ptr_value
                last_bytes = content

            time.sleep(0.3)

    except KeyboardInterrupt:
        pass
    finally:
        process.close_process(handle)


if __name__ == "__main__":
    main()
