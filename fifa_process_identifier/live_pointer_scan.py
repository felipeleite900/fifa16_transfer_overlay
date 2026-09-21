"""
Pointer scan reverso AO VIVO (sem snapshot em disco): dado um endereço
alvo atual (ex: onde encontramos o campo "overallrating" do jogador
selecionado na tela), varre toda a memória PRIVATE+COMMIT do processo
procurando ponteiros de 8 bytes que apontem para esse endereço (ou
perto dele, dentro de uma tolerância). Reporta se algum desses
ponteiros está DENTRO do módulo fifa16.exe (o que indicaria uma
variável global/estática — uma âncora ESTÁVEL entre execuções e entre
trocas de jogador na tela, ao contrário do endereço de heap alvo que é
temporário).

Uso:
    python live_pointer_scan.py <endereco_alvo_hex> [tolerance] [--levels N]

Exemplo:
    python live_pointer_scan.py 8E8C7C60 32 --levels 3
"""
from __future__ import annotations

import sys

import numpy as np

import memory
import modules
import process

sys.stdout.reconfigure(encoding="utf-8")


def get_regions_as_arrays(handle):
    all_regions = memory.enumerate_regions(handle)
    candidate_regions = [
        r for r in all_regions
        if r.state == memory.MEM_COMMIT
        and r.type == memory.MEM_PRIVATE
        and not (r.protect & memory.PAGE_GUARD)
        and r.protect != memory.PAGE_NOACCESS
        and r.size <= memory.MAX_REGION_SIZE
    ]

    result = {}
    for r in candidate_regions:
        raw = memory.read_region(handle, r)
        if raw is None:
            continue
        result[r.base] = np.frombuffer(raw, dtype=np.uint8)
    return result


def scan_pointers_to_targets(regions, targets, tolerance):
    if not targets:
        return []

    targets_arr = np.array(sorted(set(targets)), dtype=np.uint64)
    results = []

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
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target_addr = int(sys.argv[1], 16)
    tolerance = 0
    max_levels = 3

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--levels":
            max_levels = int(args[i + 1])
            i += 2
        else:
            tolerance = int(args[i])
            i += 1

    print(f"[INFO] Alvo inicial: 0x{target_addr:012X}  (tolerância={tolerance}, "
          f"max_levels={max_levels})")

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)
    mod_list = modules.list_modules(handle)
    exe_module = next(
        (m for m in mod_list if m.name.lower().endswith("fifa16.exe")), None
    )

    print("[INFO] Lendo regiões PRIVATE+COMMIT (pode demorar)...")
    regions = get_regions_as_arrays(handle)
    print(f"[INFO] {len(regions)} regiões carregadas.")

    current_targets = [target_addr]
    visited = set(current_targets)

    for level in range(1, max_levels + 1):
        print(f"\n[INFO] Nível {level}: buscando ponteiros para "
              f"{len(current_targets)} alvo(s)...")

        hits = scan_pointers_to_targets(regions, current_targets, tolerance)

        if not hits:
            print(f"[INFO] Nível {level}: nenhum ponteiro encontrado. Parando.")
            break

        print(f"[INFO] Nível {level}: {len(hits)} ponteiro(s) encontrados.")

        anchors = []
        for ptr_addr, ptr_value in hits:
            mod = modules.find_module_for_address(mod_list, ptr_addr)
            if mod is not None:
                anchors.append((ptr_addr, ptr_value, mod))

        if anchors:
            print()
            print(f"[JACKPOT] {len(anchors)} ponteiro(s) no nível {level} "
                  f"estão DENTRO de um módulo carregado:")
            for ptr_addr, ptr_value, mod in anchors:
                offset = mod.offset_of(ptr_addr)
                print(f"    {mod.name}+0x{offset:X}  (0x{ptr_addr:012X})  "
                      f"->  aponta para 0x{ptr_value:012X}")
            print()
            print("[INFO] Esses são candidatos a âncora ESTÁVEL. Anote o offset "
                  "do módulo para reusar entre sessões.")
            process.close_process(handle)
            return

        # mostra todos os hits deste nivel mesmo sem anchor, para debug
        print(f"[INFO] Nenhum ainda dentro de módulo. Amostra de até 20 ponteiros:")
        for ptr_addr, ptr_value in hits[:20]:
            print(f"    0x{ptr_addr:012X}  ->  0x{ptr_value:012X}")

        new_targets = [addr for addr, _ in hits if addr not in visited]
        if not new_targets:
            print(f"[INFO] Nível {level}: sem novos alvos (ciclo?). Parando.")
            break

        visited.update(new_targets)
        current_targets = new_targets

        if len(current_targets) > 5000:
            print(f"[WARN] Cortando nível {level} para 5000 alvos (eram {len(current_targets)}).")
            current_targets = current_targets[:5000]

    process.close_process(handle)
    print("\n[INFO] BFS concluído sem achar âncora em módulo.")


if __name__ == "__main__":
    main()
