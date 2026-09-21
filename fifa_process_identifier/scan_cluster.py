"""
Live scan (sem snapshot em disco): varre a memoria do processo FIFA16
AGORA, procurando um "cluster" de valores int32 conhecidos (ex:
atributos de um jogador visivel na tela) que aparecam PROXIMOS uns dos
outros dentro de uma janela pequena — provavel indicio de serem campos
vizinhos da mesma struct.

Somente leitura (ReadProcessMemory). Nao escreve nada.

Uso:
    python scan_cluster.py <valor1> <valor2> <valor3> ... [--window N] [--min-hits N]

Exemplo (Ibrahim Mbaye: acceleration=79, agility=80, jumping=47, strength=43):
    python scan_cluster.py 79 80 47 43 --window 256 --min-hits 3
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

import numpy as np

import memory
import modules
import process

sys.stdout.reconfigure(encoding="utf-8")


def enumerate_readable_regions(handle):
    """Como memory.enumerate_regions, mas mantém qualquer região
    COMMIT + PRIVATE (não só as consideradas 'writable' pelo filtro
    padrão), já que às vezes o protect muda dinamicamente."""
    regions = memory.enumerate_regions(handle)
    result = []
    for r in regions:
        if r.state != memory.MEM_COMMIT:
            continue
        if r.type != memory.MEM_PRIVATE:
            continue
        if r.protect & memory.PAGE_GUARD:
            continue
        if r.protect == memory.PAGE_NOACCESS:
            continue
        if r.size > memory.MAX_REGION_SIZE:
            continue
        result.append(r)
    return result


def main() -> None:
    args = sys.argv[1:]
    window = 256
    min_hits = None
    values = []

    i = 0
    while i < len(args):
        if args[i] == "--window":
            window = int(args[i + 1])
            i += 2
        elif args[i] == "--min-hits":
            min_hits = int(args[i + 1])
            i += 2
        else:
            values.append(int(args[i]))
            i += 1

    if not values:
        print(__doc__)
        sys.exit(1)

    if min_hits is None:
        min_hits = max(2, len(values) - 1)

    unique_values = sorted(set(values))
    print(f"[INFO] Procurando cluster de valores {unique_values} "
          f"(janela={window} bytes, min_hits={min_hits})...")

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)
    regions = enumerate_readable_regions(handle)
    print(f"[INFO] {len(regions)} regiões PRIVATE/COMMIT a varrer.")

    # value -> lista de endereços absolutos (alinhados a 4 bytes) onde
    # aquele int32 aparece.
    hits_by_value = {v: [] for v in unique_values}
    target_arr = np.array(unique_values, dtype=np.int32)

    regions_read = 0
    for region in regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        regions_read += 1

        usable_len = len(raw) - (len(raw) % 4)
        if usable_len == 0:
            continue

        arr = np.frombuffer(raw[:usable_len], dtype="<i4")

        # para cada valor alvo, acha posições onde arr == valor
        for v in unique_values:
            positions = np.flatnonzero(arr == v)
            for pos in positions:
                hits_by_value[v].append(region.base + pos * 4)

    process.close_process(handle)

    print(f"[INFO] {regions_read} regiões lidas com sucesso.")
    for v in unique_values:
        print(f"[INFO] valor {v}: {len(hits_by_value[v])} ocorrência(s) na memória.")

    # junta todos os hits com rótulo do valor, ordena por endereço
    all_hits = []
    for v, addrs in hits_by_value.items():
        for a in addrs:
            all_hits.append((a, v))
    all_hits.sort(key=lambda x: x[0])

    if not all_hits:
        print("[RESULT] Nenhuma ocorrência encontrada.")
        return

    print()
    print("[INFO] Buscando clusters (janela deslizante)...")

    clusters = []
    n = len(all_hits)
    start_i = 0
    for start_i in range(n):
        base_addr = all_hits[start_i][0]
        window_hits = [all_hits[start_i]]
        for j in range(start_i + 1, n):
            addr, val = all_hits[j]
            if addr - base_addr <= window:
                window_hits.append((addr, val))
            else:
                break

        distinct_values = set(v for _, v in window_hits)
        if len(distinct_values) >= min_hits:
            clusters.append((base_addr, window_hits, distinct_values))

    # remove clusters redundantes (mesmo conjunto de hits, começando
    # em posições próximas) — mantém só o de menor endereço em cada
    # "vizinhança"
    clusters.sort(key=lambda c: (-len(c[2]), c[0]))

    print(f"[RESULT] {len(clusters)} cluster(s) candidato(s) (>= {min_hits} valores distintos "
          f"numa janela de {window} bytes):")
    print()

    shown = 0
    last_shown_addr = -10**18
    for base_addr, window_hits, distinct_values in clusters:
        if base_addr - last_shown_addr < window // 2:
            continue  # provavelmente o mesmo cluster, já mostrado
        last_shown_addr = base_addr
        shown += 1
        print(f"  Cluster #{shown} — âncora em 0x{base_addr:012X} "
              f"({len(distinct_values)}/{len(unique_values)} valores distintos):")
        for addr, val in window_hits:
            print(f"      0x{addr:012X}  (offset +0x{addr - base_addr:X})  = {val}")
        print()

        if shown >= 40:
            print("[INFO] Cortando em 40 clusters exibidos.")
            break


if __name__ == "__main__":
    main()
