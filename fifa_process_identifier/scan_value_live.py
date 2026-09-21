"""
Escaneia toda a memoria PRIVATE+COMMIT do processo procurando um valor
int32 especifico, alinhado a 4 bytes. Simples e direto -- para valores
raros (como orcamento do clube) isso deve retornar poucos candidatos.

Uso:
    python scan_value_live.py <valor_int32>
"""
from __future__ import annotations

import struct
import sys

import memory
import process

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target_value = int(sys.argv[1])
    needle = struct.pack("<i", target_value)

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

    print(f"[INFO] Procurando valor {target_value} em {len(candidate_regions)} regiões...")

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
            if pos % 4 == 0:
                found.append(region.base + pos)
            start = pos + 1

    process.close_process(handle)

    print(f"[RESULT] {len(found)} ocorrência(s) alinhadas a 4 bytes:")
    for addr in found:
        print(f"    0x{addr:012X}")


if __name__ == "__main__":
    main()
