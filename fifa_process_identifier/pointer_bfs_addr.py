"""
Como pointer_bfs.py, mas partindo de um ENDEREÇO específico (não de
uma string) como nível 0. Útil para continuar a busca a partir de um
"objeto hub" já identificado por find_hub.py.

Uso:
    python pointer_bfs_addr.py <snapshot_name> <address_hex> [max_levels] [tolerance]
"""

from __future__ import annotations

import sys

import modules
import process
from pointer_bfs import load_all_regions, scan_pointers_to_targets


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python pointer_bfs_addr.py <snapshot_name> <address_hex> [max_levels] [tolerance]")
        sys.exit(1)

    snapshot_name = sys.argv[1]
    start_address = int(sys.argv[2], 16)
    max_levels = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    tolerance = int(sys.argv[4]) if len(sys.argv) > 4 else 32

    print(f"[INFO] Carregando snapshot '{snapshot_name}'...")
    regions = load_all_regions(snapshot_name)
    print(f"[INFO] {len(regions)} regiões carregadas.")

    pid = process.find_process_by_name("FIFA16.exe")
    mod_list = []
    if pid is not None:
        handle = process.open_process(pid)
        mod_list = modules.list_modules(handle)
        process.close_process(handle)
        print(f"[INFO] {len(mod_list)} módulos carregados.")

    current_targets = [start_address]
    visited_targets: set[int] = set(current_targets)

    print(f"[INFO] Nível 0: 0x{start_address:012X}")

    for level in range(1, max_levels + 1):
        print(f"[INFO] Buscando ponteiros para o nível {level - 1} "
              f"({len(current_targets)} alvos)...")

        hits = scan_pointers_to_targets(regions, current_targets, tolerance)

        if not hits:
            print(f"[INFO] Nível {level}: nenhum ponteiro encontrado. Parando.")
            break

        print(f"[INFO] Nível {level}: {len(hits)} ponteiros encontrados.")

        anchors = []
        for ptr_addr, ptr_value in hits:
            mod = modules.find_module_for_address(mod_list, ptr_addr)
            if mod is not None:
                anchors.append((ptr_addr, ptr_value, mod))

        if anchors:
            print()
            print(f"[JACKPOT] {len(anchors)} ponteiro(s) no nível {level} "
                  f"estão DENTRO de um módulo:")
            for ptr_addr, ptr_value, mod in anchors:
                offset = mod.offset_of(ptr_addr)
                print(
                    f"    {mod.name}+0x{offset:X}  (0x{ptr_addr:012X})  "
                    f"->  aponta para 0x{ptr_value:012X}"
                )
            return

        new_targets = [addr for addr, _ in hits if addr not in visited_targets]

        if not new_targets:
            print(f"[INFO] Nível {level}: sem novos alvos (ciclo?). Parando.")
            break

        visited_targets.update(new_targets)
        current_targets = new_targets

        if len(current_targets) > 20000:
            print(f"[WARN] Cortando nível {level} para 20000 alvos.")
            current_targets = current_targets[:20000]

    print()
    print("[INFO] BFS concluído sem achar âncora em módulo.")
    print(f"[INFO] Últimos {min(30, len(current_targets))} candidatos:")
    for addr in current_targets[:30]:
        print(f"    0x{addr:012X}")


if __name__ == "__main__":
    main()
