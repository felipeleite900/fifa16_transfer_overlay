"""
Acha o(s) endereco(s) de memoria que guardam o playerid do jogador
ATUALMENTE exibido na tela (o "slot" de selecao ativa), varrendo por
esse int32 especifico e comparando entre duas capturas com jogadores
diferentes na tela.

Uso:
    Passo 1 (jogador A na tela):
        python find_selected_player_slot.py scan A <playerid_A>
    Passo 2 (jogador B na tela):
        python find_selected_player_slot.py scan B <playerid_B>
    Passo 3 (intersecao):
        python find_selected_player_slot.py diff

Os resultados de cada scan sao salvos em disco (JSON) para permitir
rodar em 2 execucoes separadas do processo entre trocas de tela.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import memory
import process

sys.stdout.reconfigure(encoding="utf-8")

RESULTS_DIR = Path(__file__).parent / "selected_player_scan"
RESULTS_DIR.mkdir(exist_ok=True)


def scan_for_value(target_value: int) -> list[int]:
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

    print(f"[INFO] {len(candidate_regions)} regiões candidatas (PRIVATE+COMMIT).")

    target_bytes = struct.pack("<i", target_value)

    found = []
    regions_read = 0
    for region in candidate_regions:
        raw = memory.read_region(handle, region)
        if raw is None:
            continue
        regions_read += 1
        start = 0
        while True:
            pos = raw.find(target_bytes, start)
            if pos == -1:
                break
            # exige alinhamento de 4 bytes (mais provável para um campo int)
            abs_addr = region.base + pos
            if abs_addr % 4 == 0:
                found.append(abs_addr)
            start = pos + 1

    process.close_process(handle)

    print(f"[INFO] {regions_read} regiões lidas. {len(found)} ocorrência(s) "
          f"alinhadas a 4 bytes de {target_value}.")
    return found


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action == "scan":
        label = sys.argv[2]
        target_value = int(sys.argv[3])
        addrs = scan_for_value(target_value)

        out_path = RESULTS_DIR / f"scan_{label}.json"
        out_path.write_text(json.dumps({"value": target_value, "addresses": addrs}), encoding="utf-8")
        print(f"[OK] Salvo em {out_path} ({len(addrs)} endereços).")

    elif action == "diff":
        scan_files = sorted(RESULTS_DIR.glob("scan_*.json"))
        if len(scan_files) < 2:
            print(f"[ERROR] Preciso de pelo menos 2 scans salvos. Achei {len(scan_files)}.")
            sys.exit(1)

        scans = []
        for f in scan_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            scans.append((f.stem, data["value"], set(data["addresses"])))
            print(f"  {f.stem}: valor={data['value']} endereços={len(data['addresses'])}")

        # Intersecao: enderecos presentes em TODOS os scans (mesmo
        # endereco, mudou de um valor pro outro entre capturas)
        common = scans[0][2]
        for _, _, addrs in scans[1:]:
            common &= addrs

        print(f"\n[RESULT] {len(common)} endereço(s) presentes em TODOS os scans "
              f"(candidatos fortes a 'slot de jogador selecionado'):")
        for addr in sorted(common):
            print(f"    0x{addr:012X}")

    else:
        print(f"Ação desconhecida: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
