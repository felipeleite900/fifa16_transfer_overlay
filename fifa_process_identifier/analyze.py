"""
Utilitário de análise: compara um diff "real" (transição de tela)
contra um diff de "ruído" (mesma tela, apenas passou o tempo) e
mostra somente os endereços que mudaram na transição mas NÃO no
ruído — candidatos genuínos a representar estado de UI/gameplay
relacionado à navegação.

Uso:
    python analyze.py <snapshot_antes> <snapshot_depois> <ruido_antes_2> <ruido_depois_2> [ruido_antes_1b]

Onde:
    - snapshot_antes / snapshot_depois: transição real de tela (A -> B)
    - ruido_antes_2: outro snapshot tirado na MESMA tela A (parado, sem navegar)
    - ruido_depois_2: outro snapshot tirado na MESMA tela B (parado, sem navegar)

O script remove qualquer endereço que também mude dentro da tela A
sozinha OU dentro da tela B sozinha, sobrando só endereços que mudam
especificamente por causa da navegação A -> B.
"""

from __future__ import annotations

import sys

import memory


def main() -> None:
    if len(sys.argv) != 5:
        print(
            "Uso: python analyze.py <antes> <depois> <ruido_antes_2> <ruido_depois_2>"
        )
        sys.exit(1)

    before, after, noise_before_2, noise_after_2 = sys.argv[1:5]

    print(f"[INFO] Calculando diff real: {before} -> {after}")
    real_changes = memory.diff_snapshots(before, after)
    print(f"[INFO] {len(real_changes)} mudanças na transição real.")

    print(f"[INFO] Calculando ruído na tela ANTES: {before} -> {noise_before_2}")
    noise_before = memory.diff_snapshots(before, noise_before_2)
    print(f"[INFO] {len(noise_before)} mudanças de ruído (tela antes, parado).")

    print(f"[INFO] Calculando ruído na tela DEPOIS: {after} -> {noise_after_2}")
    noise_after = memory.diff_snapshots(after, noise_after_2)
    print(f"[INFO] {len(noise_after)} mudanças de ruído (tela depois, parado).")

    noise_addrs = set(c.address for c in noise_before) | set(
        c.address for c in noise_after
    )

    candidates = [c for c in real_changes if c.address not in noise_addrs]

    print()
    print(f"[RESULT] {len(candidates)} candidatos genuínos "
          f"(mudaram na transição, não no ruído).")
    print()

    out_path = "candidates.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(c.describe() + "\n")

    print(f"[INFO] Lista completa salva em {out_path}")

    # Mostra uma amostra no console, priorizando mudanças "pequenas"
    # (1-4 bytes), que são as candidatas mais prováveis a serem um
    # enum/flag de tela ou um ID.
    small_candidates = [c for c in candidates if len(c.old) <= 4]
    print()
    print(f"[INFO] {len(small_candidates)} candidatos com bloco <= 4 bytes "
          f"(mais prováveis de ser um enum/flag/id):")
    print()

    for c in small_candidates[:50]:
        print("  " + c.describe())

    if len(small_candidates) > 50:
        print(f"  ... e mais {len(small_candidates) - 50} (veja {out_path})")


if __name__ == "__main__":
    main()
