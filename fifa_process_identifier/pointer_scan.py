"""
Pointer scan passivo (somente leitura — nunca escreve na memória do
FIFA nem intercepta execução, portanto não deve causar crashes).

Ideia:
    1. Localiza todos os endereços absolutos onde uma string alvo
       (ex: b"TransferPlayerSearch") aparece na memória.
    2. Varre todas as regiões do snapshot procurando sequências de 8
       bytes (ponteiro x64, little-endian) cujo valor numérico seja
       IGUAL a um desses endereços (ou muito próximo, para cobrir o
       caso de a string estar embutida dentro de uma struct maior e o
       ponteiro apontar para o começo dela).
    3. Reporta "quem aponta para a string" — esses são candidatos
       fortes a serem a variável de estado (ex: current screen name,
       active ViewModel) que o jogo usa internamente.

Uso:
    python pointer_scan.py <snapshot_name> <string_alvo> [tolerancia_bytes]
"""

from __future__ import annotations

import struct
import sys

import numpy as np

import memory


def find_string_addresses(snapshot_name: str, needle: bytes) -> list[int]:
    """Retorna a lista de endereços absolutos onde `needle` aparece."""

    raw = memory.load_snapshot(snapshot_name)
    addresses = []

    for base, data in raw.items():
        start = 0
        while True:
            pos = data.find(needle, start)
            if pos == -1:
                break
            addresses.append(base + pos)
            start = pos + 1

    return addresses


def scan_pointers_to(
    snapshot_name: str, targets: list[int], tolerance: int = 0
) -> list[tuple[int, int]]:
    """
    Varre o snapshot procurando ponteiros de 8 bytes cujo valor caia
    dentro de [target, target + tolerance] para algum target da lista.

    Retorna lista de (endereco_do_ponteiro, valor_apontado).
    """

    raw = memory.load_snapshot(snapshot_name)
    targets_arr = np.array(sorted(targets), dtype=np.uint64)

    results = []

    for base, data in raw.items():
        if len(data) < 8:
            continue

        # visão como array de uint64 alinhado a cada byte é caro;
        # fazemos alinhado a 8 bytes primeiro (mais comum para
        # ponteiros reais em structs), depois podemos relaxar.
        usable_len = len(data) - (len(data) % 8)
        if usable_len == 0:
            continue

        arr = np.frombuffer(data[:usable_len], dtype="<u8")

        # para cada valor no array, verifica se está dentro de
        # [target, target+tolerance] de algum target.
        # Como targets pode ser grande, fazemos busca vetorizada:
        # usamos searchsorted para achar o target mais próximo.
        idx = np.searchsorted(targets_arr, arr)
        idx_clamped = np.clip(idx, 0, len(targets_arr) - 1)
        nearest = targets_arr[idx_clamped]

        diff = arr.astype(np.int64) - nearest.astype(np.int64)
        mask = (diff >= 0) & (diff <= tolerance)

        # também checa o vizinho anterior (searchsorted pode "passar")
        idx_prev = np.clip(idx - 1, 0, len(targets_arr) - 1)
        nearest_prev = targets_arr[idx_prev]
        diff_prev = arr.astype(np.int64) - nearest_prev.astype(np.int64)
        mask_prev = (diff_prev >= 0) & (diff_prev <= tolerance)

        final_mask = mask | mask_prev

        hit_positions = np.flatnonzero(final_mask)

        for pos in hit_positions:
            ptr_addr = base + pos * 8
            ptr_value = int(arr[pos])
            results.append((ptr_addr, ptr_value))

    return results


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python pointer_scan.py <snapshot_name> <string_alvo> [tolerancia]")
        sys.exit(1)

    snapshot_name = sys.argv[1]
    needle = sys.argv[2].encode()
    tolerance = int(sys.argv[3]) if len(sys.argv) > 3 else 64

    print(f"[INFO] Procurando ocorrências de {needle!r} em '{snapshot_name}'...")
    targets = find_string_addresses(snapshot_name, needle)

    if not targets:
        print("[INFO] String não encontrada nesse snapshot.")
        return

    print(f"[INFO] {len(targets)} ocorrências encontradas:")
    for t in targets:
        print(f"    0x{t:012X}")

    print()
    print(f"[INFO] Procurando ponteiros (tolerância {tolerance} bytes)...")
    hits = scan_pointers_to(snapshot_name, targets, tolerance)

    print()
    print(f"[RESULT] {len(hits)} ponteiros encontrados apontando para a string:")
    for ptr_addr, ptr_value in hits:
        offset_from_nearest = min(abs(ptr_value - t) for t in targets)
        print(
            f"    ponteiro em 0x{ptr_addr:012X}  ->  aponta para 0x{ptr_value:012X} "
            f"(offset {offset_from_nearest})"
        )


if __name__ == "__main__":
    main()
