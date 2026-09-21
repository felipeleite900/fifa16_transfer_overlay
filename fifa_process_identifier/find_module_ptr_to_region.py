"""
Procura, dentro das regiões do PROPRIO modulo fifa16.exe (seções de
dados globais/estaticas, tipicamente MEM_IMAGE com protect
READWRITE), qualquer ponteiro de 8 bytes cujo valor caia dentro de um
intervalo de endereços alvo (ex: uma regiao de heap grande onde
encontramos objetos de jogador "vivos"). Isso ajuda a achar o
"gerenciador"/"pool" global que referencia esses objetos, que serviria
de ancora estavel para uma cadeia de ponteiros.

Uso:
    python find_module_ptr_to_region.py <region_base_hex> <region_size_hex>
"""
from __future__ import annotations

import struct
import sys

import memory
import modules
import process

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    region_base = int(sys.argv[1], 16)
    region_size = int(sys.argv[2], 16)
    region_end = region_base + region_size

    print(f"[INFO] Procurando ponteiros para [0x{region_base:012X}, 0x{region_end:012X})")

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)
    mod_list = modules.list_modules(handle)
    exe_module = next(
        (m for m in mod_list if m.name.lower().endswith("fifa16.exe")), None
    )
    if exe_module is None:
        print("[ERROR] fifa16.exe não encontrado nos módulos.")
        sys.exit(1)

    print(f"[INFO] fifa16.exe: base=0x{exe_module.base:012X} size=0x{exe_module.size:X}")

    # Varre TODAS as regiões que fazem parte do range do módulo exe
    # (pode ser múltiplas regiões de proteção diferente dentro do
    # mesmo espaço de endereçamento do módulo).
    all_regions = memory.enumerate_regions(handle)
    module_regions = [
        r for r in all_regions
        if r.state == memory.MEM_COMMIT
        and exe_module.base <= r.base < exe_module.end
        and not (r.protect & memory.PAGE_GUARD)
        and r.protect != memory.PAGE_NOACCESS
    ]

    print(f"[INFO] {len(module_regions)} região(ões) dentro do range do módulo.")

    found = []
    for r in module_regions:
        raw = memory.read_region(handle, r)
        if raw is None:
            continue
        usable_len = len(raw) - (len(raw) % 8)
        for off in range(0, usable_len, 8):
            val = struct.unpack_from("<Q", raw, off)[0]
            if region_base <= val < region_end:
                abs_addr = r.base + off
                found.append((abs_addr, val))

    process.close_process(handle)

    print(f"\n[RESULT] {len(found)} ponteiro(s) dentro do módulo apontando para a região:")
    for abs_addr, val in found[:100]:
        offset = abs_addr - exe_module.base
        print(f"    fifa16.exe+0x{offset:X}  (0x{abs_addr:012X})  ->  0x{val:012X}")

    if len(found) > 100:
        print(f"    ... e mais {len(found) - 100} não exibidos.")


if __name__ == "__main__":
    main()
