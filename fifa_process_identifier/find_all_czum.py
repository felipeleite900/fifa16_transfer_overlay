"""
Procura TODAS as ocorrencias da string "CZUM" (shortname da tabela de
jogadores) em toda a memoria do processo -- nao so onde ja achamos um
cabecalho de database completo. Isso ajuda a descobrir se existem
MULTIPLAS copias da tabela (ex: uma "read-only" usada soh para
snapshot/save, e outra "live" realmente usada pela UI).
"""
from __future__ import annotations

import sys

import memory
import process

sys.stdout.reconfigure(encoding="utf-8")

NEEDLE = b"CZUM"


def main() -> None:
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

    print(f"[INFO] {len(candidate_regions)} regiões candidatas.")

    found = []
    for region in candidate_regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        start = 0
        while True:
            pos = raw.find(NEEDLE, start)
            if pos == -1:
                break
            abs_addr = region.base + pos
            found.append((abs_addr, region.base, region.size, region.protect))
            start = pos + 1

    process.close_process(handle)

    print(f"[RESULT] {len(found)} ocorrência(s) de 'CZUM':")
    for abs_addr, region_base, region_size, protect in found:
        print(f"    0x{abs_addr:012X}  (região base=0x{region_base:012X} "
              f"size=0x{region_size:X} protect=0x{protect:X})")


if __name__ == "__main__":
    main()
