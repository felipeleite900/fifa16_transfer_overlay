"""
Procura a assinatura de database FIFA (t3db v8: "DB\x00\x08\x00\x00\x00\x00")
diretamente na memoria do processo fifa16.exe, AO VIVO (sem snapshot em
disco). Isso testa a hipotese de que o motor mantem as mesmas estruturas
de banco de dados binarias (como a tabela CZUM de jogadores) residentes
em RAM durante toda a sessao de carreira -- nao apenas quando uma tela
especifica esta aberta.

Somente leitura (ReadProcessMemory). Nao escreve nada.

Uso:
    python find_db_in_memory.py
"""
from __future__ import annotations

import sys

import memory
import modules
import process

sys.stdout.reconfigure(encoding="utf-8")

DB_SIGNATURE = b"DB\x00\x08\x00\x00\x00\x00"


def main() -> None:
    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)
    mod_list = modules.list_modules(handle)

    # Varre TODAS as regiões PRIVATE + COMMIT (heap dinâmico), sem
    # filtrar por proteção de escrita (as databases podem estar em
    # páginas somente-leitura depois de carregadas).
    all_regions = memory.enumerate_regions(handle)
    candidate_regions = [
        r for r in all_regions
        if r.state == memory.MEM_COMMIT
        and r.type == memory.MEM_PRIVATE
        and not (r.protect & memory.PAGE_GUARD)
        and r.protect != memory.PAGE_NOACCESS
        and r.size <= memory.MAX_REGION_SIZE
    ]

    print(f"[INFO] {len(all_regions)} regiões totais, "
          f"{len(candidate_regions)} candidatas (PRIVATE+COMMIT, legíveis).")

    found = []
    regions_read = 0
    bytes_read_total = 0

    for region in candidate_regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        regions_read += 1
        bytes_read_total += len(raw)

        start = 0
        while True:
            pos = raw.find(DB_SIGNATURE, start)
            if pos == -1:
                break
            abs_addr = region.base + pos
            found.append((abs_addr, region.base, region.size, region.protect))
            start = pos + 1

    process.close_process(handle)

    print(f"[INFO] {regions_read} regiões lidas com sucesso "
          f"({bytes_read_total / (1024*1024):.1f} MB no total).")
    print()
    print(f"[RESULT] {len(found)} ocorrência(s) da assinatura de database encontrada(s):")
    for abs_addr, region_base, region_size, protect in found:
        print(f"    0x{abs_addr:012X}  (região base=0x{region_base:012X} "
              f"size=0x{region_size:X} protect=0x{protect:X})")


if __name__ == "__main__":
    main()
