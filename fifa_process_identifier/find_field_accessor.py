"""
Procura por marcadores de debug no formato "CZUM<shortname_do_campo>"
(8 bytes ASCII) na memoria do processo -- descoberta desta sessao:
esses marcadores parecem identificar "accessors" individuais de campo
usados pela engine/UI para ler/escrever um campo especifico do
jogador atualmente selecionado.

Uso:
    python find_field_accessor.py <table_shortname_4_chars> <field_shortname_4_chars> [--dump N]

Exemplo (CZUM.strength = "nmgT"):
    python find_field_accessor.py CZUM nmgT --dump 64
"""
from __future__ import annotations

import struct
import sys

import memory
import process

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    table_shortname = sys.argv[1]
    field_shortname = sys.argv[2]
    if len(table_shortname) != 4 or len(field_shortname) != 4:
        print("[ERROR] table_shortname e field_shortname devem ter exatamente 4 caracteres cada.")
        sys.exit(1)

    dump_size = 0
    if "--dump" in sys.argv:
        idx = sys.argv.index("--dump")
        dump_size = int(sys.argv[idx + 1])

    needle = table_shortname.encode("ascii") + field_shortname.encode("ascii")
    print(f"[INFO] Procurando marcador {needle!r} na memória...")

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)

    all_regions = memory.enumerate_regions(handle)
    candidate_regions = [
        r for r in all_regions
        if r.state == memory.MEM_COMMIT
        and r.type == memory.MEM_PRIVATE
        and not (r.protect & memory.PAGE_GUARD)
        and r.protect != memory.PAGE_NOACCESS
        and r.size <= memory.MAX_REGION_SIZE
    ]

    found = []
    for region in candidate_regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        start = 0
        while True:
            pos = raw.find(needle, start)
            if pos == -1:
                break
            abs_addr = region.base + pos
            found.append(abs_addr)
            start = pos + 1

    print(f"[RESULT] {len(found)} ocorrência(s) encontradas:")
    for addr in found:
        print(f"    0x{addr:012X}")

        if dump_size:
            buf_size = dump_size
            import ctypes
            buf = ctypes.create_string_buffer(buf_size)
            read = ctypes.c_size_t(0)
            memory.ReadProcessMemory(
                handle, ctypes.c_void_p(addr), buf, buf_size, ctypes.byref(read)
            )
            data = buf.raw[: read.value]
            for off in range(0, len(data), 8):
                if off + 8 <= len(data):
                    val = struct.unpack_from("<Q", data, off)[0]
                    val_i32 = struct.unpack_from("<i", data, off)[0] if off + 4 <= len(data) else None
                    print(f"        +0x{off:03X}: 0x{val:016X}  (low32 as int32={val_i32})")

    process.close_process(handle)


if __name__ == "__main__":
    main()
