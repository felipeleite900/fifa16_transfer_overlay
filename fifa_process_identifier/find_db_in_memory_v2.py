"""
Como find_db_in_memory.py, mas varre TODOS os tipos de região
(PRIVATE, MAPPED, e opcionalmente IMAGE), não só PRIVATE. A cópia
"viva" da database (se existir separada do blob já encontrado) pode
estar em memória mapeada (MEM_MAPPED) em vez de heap privado.

Também reporta quantas ocorrências de CZUM existem em cada tipo de
região, para comparar.
"""
from __future__ import annotations

import sys

import memory
import process

sys.stdout.reconfigure(encoding="utf-8")

DB_SIGNATURE = b"DB\x00\x08\x00\x00\x00\x00"

TYPE_NAMES = {
    memory.MEM_PRIVATE: "PRIVATE",
    memory.MEM_IMAGE: "IMAGE",
    memory.MEM_MAPPED: "MAPPED",
}


def main() -> None:
    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)

    all_regions = memory.enumerate_regions(handle)

    candidate_regions = []
    for r in all_regions:
        if r.state != memory.MEM_COMMIT:
            continue
        if r.protect & memory.PAGE_GUARD:
            continue
        if r.protect == memory.PAGE_NOACCESS:
            continue
        if r.size > memory.MAX_REGION_SIZE:
            continue
        candidate_regions.append(r)

    by_type = {}
    for r in candidate_regions:
        by_type.setdefault(r.type, 0)
        by_type[r.type] += 1

    print(f"[INFO] {len(all_regions)} regiões totais, {len(candidate_regions)} candidatas.")
    for t, count in by_type.items():
        print(f"    tipo {TYPE_NAMES.get(t, hex(t))}: {count} regiões")

    found = []
    regions_read = 0
    bytes_total = 0

    for region in candidate_regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        regions_read += 1
        bytes_total += len(raw)

        start = 0
        while True:
            pos = raw.find(DB_SIGNATURE, start)
            if pos == -1:
                break
            abs_addr = region.base + pos
            found.append((abs_addr, region.base, region.size, region.protect, region.type))
            start = pos + 1

    process.close_process(handle)

    print(f"\n[INFO] {regions_read} regiões lidas ({bytes_total/(1024*1024):.1f} MB).")
    print(f"\n[RESULT] {len(found)} ocorrência(s) da assinatura de database:")
    for abs_addr, region_base, region_size, protect, rtype in found:
        type_name = TYPE_NAMES.get(rtype, hex(rtype))
        print(f"    0x{abs_addr:012X}  (região base=0x{region_base:012X} "
              f"size=0x{region_size:X} protect=0x{protect:X} type={type_name})")


if __name__ == "__main__":
    main()
