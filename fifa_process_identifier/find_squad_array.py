"""
Procura um ARRAY contiguo de playerids na memoria (ex: tela de
Elenco/Squad que lista varios jogadores de uma vez). Se existir, os
playerids devem aparecer proximos uns dos outros com um "stride"
(passo) constante entre eles -- indicando um array de structs, ideal
para escrita em lote.

Uso:
    python find_squad_array.py <playerid1> <playerid2> ... <playeridN>
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

    target_ids = [int(x) for x in sys.argv[1:]]
    print(f"[INFO] Procurando {len(target_ids)} playerids: {target_ids}")

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

    # value -> list of absolute addresses (4-byte aligned)
    hits_by_id = {tid: [] for tid in target_ids}

    for region in candidate_regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        usable_len = len(raw) - (len(raw) % 4)
        if usable_len == 0:
            continue

        for tid in target_ids:
            needle = struct.pack("<i", tid)
            start = 0
            while True:
                pos = raw.find(needle, start)
                if pos == -1:
                    break
                if pos % 4 == 0:
                    hits_by_id[tid].append(region.base + pos)
                start = pos + 1

    process.close_process(handle)

    for tid, addrs in hits_by_id.items():
        print(f"[INFO] playerid {tid}: {len(addrs)} ocorrência(s).")

    # junta todos os hits com rotulo, ordena por endereco
    all_hits = []
    for tid, addrs in hits_by_id.items():
        for a in addrs:
            all_hits.append((a, tid))
    all_hits.sort(key=lambda x: x[0])

    print(f"\n[INFO] {len(all_hits)} ocorrências totais, ordenadas por endereço.")

    # procura por sequencias onde varios ids DIFERENTES aparecem com
    # espacamento regular (stride) -- forte indicio de array
    WINDOW = 1024 * 64  # 64KB de janela para considerar "perto"
    MIN_DISTINCT = min(4, len(target_ids))

    clusters = []
    n = len(all_hits)
    for i in range(n):
        base_addr = all_hits[i][0]
        window_hits = [all_hits[i]]
        for j in range(i + 1, n):
            addr, tid = all_hits[j]
            if addr - base_addr <= WINDOW:
                window_hits.append((addr, tid))
            else:
                break
        distinct = set(t for _, t in window_hits)
        if len(distinct) >= MIN_DISTINCT:
            clusters.append((base_addr, window_hits, distinct))

    clusters.sort(key=lambda c: (-len(c[2]), c[0]))

    print(f"\n[RESULT] {len(clusters)} cluster(s) candidato(s) (>= {MIN_DISTINCT} "
          f"ids distintos numa janela de {WINDOW} bytes):")

    shown = 0
    last_shown = -10**18
    for base_addr, window_hits, distinct in clusters:
        if base_addr - last_shown < WINDOW // 2:
            continue
        last_shown = base_addr
        shown += 1
        print(f"\n  Cluster #{shown} — âncora em 0x{base_addr:012X} "
              f"({len(distinct)}/{len(target_ids)} ids distintos):")
        for addr, tid in window_hits[:40]:
            print(f"      0x{addr:012X}  (offset +0x{addr - base_addr:X})  playerid={tid}")

        if shown >= 20:
            print("\n[INFO] Cortando em 20 clusters exibidos.")
            break


if __name__ == "__main__":
    main()
