"""
Pointer scan multi-nível (BFS), 100% passivo (apenas leitura de
memória já capturada em snapshot — não interage com o processo vivo,
não usa breakpoints, não pode causar crash).

Ideia:
    Nível 0: endereços onde a string alvo aparece.
    Nível 1: endereços que contêm um ponteiro para o nível 0.
    Nível 2: endereços que contêm um ponteiro para algum endereço do
             nível 1.
    ... e assim por diante.

A cada nível, verificamos se algum dos ponteiros encontrados está
localizado DENTRO de um módulo carregado (fifa16.exe, fifa16.bin,
alguma DLL) — isso indicaria uma variável global/estática, que é uma
"âncora" estável entre execuções do jogo (ao contrário de endereços
de heap, que mudam a cada execução).

Uso:
    python pointer_bfs.py <snapshot_name> <string_alvo> [max_levels] [tolerance]
"""

from __future__ import annotations

import sys

import numpy as np

import memory
import modules
import process


def load_all_regions(snapshot_name: str) -> dict[int, np.ndarray]:
    raw = memory.load_snapshot(snapshot_name)
    return {base: np.frombuffer(data, dtype=np.uint8) for base, data in raw.items()}


def find_string_addresses(regions: dict[int, np.ndarray], needle: bytes) -> list[int]:
    addresses = []
    needle_bytes = bytes(needle)

    for base, arr in regions.items():
        data = arr.tobytes()
        start = 0
        while True:
            pos = data.find(needle_bytes, start)
            if pos == -1:
                break
            addresses.append(base + pos)
            start = pos + 1

    return addresses


def scan_pointers_to_targets(
    regions: dict[int, np.ndarray], targets: list[int], tolerance: int
) -> list[tuple[int, int]]:
    """
    Retorna lista de (endereco_do_ponteiro, valor_apontado) para todo
    ponteiro de 8 bytes alinhado que caia em [target, target+tolerance]
    para algum target.
    """

    if not targets:
        return []

    targets_arr = np.array(sorted(set(targets)), dtype=np.uint64)
    results: list[tuple[int, int]] = []

    for base, arr in regions.items():
        usable_len = len(arr) - (len(arr) % 8)
        if usable_len < 8:
            continue

        ptrs = arr[:usable_len].view("<u8")

        idx = np.searchsorted(targets_arr, ptrs)
        idx_clamped = np.clip(idx, 0, len(targets_arr) - 1)
        nearest = targets_arr[idx_clamped]
        diff = ptrs.astype(np.int64) - nearest.astype(np.int64)
        mask = (diff >= 0) & (diff <= tolerance)

        idx_prev = np.clip(idx - 1, 0, len(targets_arr) - 1)
        nearest_prev = targets_arr[idx_prev]
        diff_prev = ptrs.astype(np.int64) - nearest_prev.astype(np.int64)
        mask_prev = (diff_prev >= 0) & (diff_prev <= tolerance)

        final_mask = mask | mask_prev
        hit_positions = np.flatnonzero(final_mask)

        for pos in hit_positions:
            ptr_addr = base + int(pos) * 8
            ptr_value = int(ptrs[pos])
            results.append((ptr_addr, ptr_value))

    return results


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python pointer_bfs.py <snapshot_name> <string_alvo> [max_levels] [tolerance]")
        sys.exit(1)

    snapshot_name = sys.argv[1]
    needle = sys.argv[2].encode()
    max_levels = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    tolerance = int(sys.argv[4]) if len(sys.argv) > 4 else 64

    print(f"[INFO] Carregando snapshot '{snapshot_name}'...")
    regions = load_all_regions(snapshot_name)
    print(f"[INFO] {len(regions)} regiões carregadas.")

    print(f"[INFO] Obtendo módulos carregados do processo (para checar âncoras)...")
    pid = process.find_process_by_name("FIFA16.exe")
    mod_list = []
    if pid is not None:
        try:
            handle = process.open_process(pid)
            mod_list = modules.list_modules(handle)
            process.close_process(handle)
            print(f"[INFO] {len(mod_list)} módulos carregados.")
        except Exception as e:
            print(f"[WARN] Não foi possível listar módulos: {e}")
    else:
        print("[WARN] FIFA não está rodando agora — não será possível checar módulos.")

    print(f"[INFO] Procurando ocorrências de {needle!r}...")
    current_targets = find_string_addresses(regions, needle)
    print(f"[INFO] Nível 0: {len(current_targets)} ocorrências da string.")

    visited_targets: set[int] = set(current_targets)

    for level in range(1, max_levels + 1):
        print()
        print(f"[INFO] Buscando ponteiros para o nível {level - 1} "
              f"({len(current_targets)} alvos)...")

        hits = scan_pointers_to_targets(regions, current_targets, tolerance)

        if not hits:
            print(f"[INFO] Nível {level}: nenhum ponteiro encontrado. Parando BFS.")
            break

        print(f"[INFO] Nível {level}: {len(hits)} ponteiros encontrados.")

        # Verifica quais desses ponteiros estão dentro de um módulo
        anchors = []
        for ptr_addr, ptr_value in hits:
            mod = modules.find_module_for_address(mod_list, ptr_addr)
            if mod is not None:
                anchors.append((ptr_addr, ptr_value, mod))

        if anchors:
            print()
            print(f"[JACKPOT] {len(anchors)} ponteiro(s) no nível {level} "
                  f"estão DENTRO de um módulo (âncora estável!):")
            for ptr_addr, ptr_value, mod in anchors:
                offset = mod.offset_of(ptr_addr)
                print(
                    f"    {mod.name}+0x{offset:X}  "
                    f"(0x{ptr_addr:012X})  ->  aponta para 0x{ptr_value:012X}"
                )
            print()
            print("[INFO] Esses são os melhores candidatos para uma cadeia de")
            print("       ponteiros ESTÁVEL entre execuções do jogo. BFS encerrado.")
            return

        # prepara próximo nível: endereços dos ponteiros que acabamos
        # de achar viram os novos alvos
        new_targets = [addr for addr, _ in hits if addr not in visited_targets]

        if not new_targets:
            print(f"[INFO] Nível {level}: todos os alvos já visitados (possível ciclo). Parando.")
            break

        visited_targets.update(new_targets)
        current_targets = new_targets

        if len(current_targets) > 20000:
            print(
                f"[WARN] Nível {level} tem {len(current_targets)} alvos — "
                f"muito ruído, cortando para os primeiros 20000 para não explodir."
            )
            current_targets = current_targets[:20000]

    print()
    print("[INFO] BFS concluído sem encontrar âncora dentro de um módulo.")
    print("[INFO] Últimos candidatos (nível final):")
    for addr in current_targets[:50]:
        print(f"    0x{addr:012X}")


if __name__ == "__main__":
    main()
