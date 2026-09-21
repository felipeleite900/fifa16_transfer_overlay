"""
Procura, entre os ponteiros de nível 1 que apontam para ocorrências de
uma string alvo, se existe um "objeto hub" — um endereço próximo ao
início da string que recebe MUITAS referências (fan-in alto). Isso
tende a indicar um singleton/objeto amplamente usado (ex: ViewModel
ativo), similar ao padrão que já observamos para TransferPlayerSearch.

Uso:
    python find_hub.py <snapshot_name> <string_alvo> [tolerance]
"""

from __future__ import annotations

import sys
from collections import Counter

import pointer_scan


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python find_hub.py <snapshot_name> <string_alvo> [tolerance]")
        sys.exit(1)

    snapshot_name = sys.argv[1]
    needle = sys.argv[2].encode()
    tolerance = int(sys.argv[3]) if len(sys.argv) > 3 else 64

    targets = pointer_scan.find_string_addresses(snapshot_name, needle)
    print(f"[INFO] {len(targets)} ocorrências de {needle!r}.")

    hits = pointer_scan.scan_pointers_to(snapshot_name, targets, tolerance)
    print(f"[INFO] {len(hits)} ponteiros encontrados.")

    counts = Counter(ptr_value for _, ptr_value in hits)
    most_common = counts.most_common(10)

    print()
    print("[RESULT] Endereços mais referenciados (candidatos a 'hub'):")
    for value, count in most_common:
        print(f"    0x{value:012X}  <- referenciado por {count} ponteiro(s)")


if __name__ == "__main__":
    main()
