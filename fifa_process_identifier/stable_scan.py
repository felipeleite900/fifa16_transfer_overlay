"""
Scan de 4 estados (técnica clássica de memory scanning, tipo Cheat
Engine): em vez de simplesmente comparar "antes vs depois" e excluir
ruído par a par (o que se mostrou insuficiente, já que o FIFA altera
uma quantidade enorme de memória continuamente mesmo parado em um
menu), procuramos endereços que sejam:

    1. ESTÁVEIS dentro da tela A (state_a == state_a2, byte a byte)
    2. ESTÁVEIS dentro da tela B (state_b == state_b2, byte a byte)
    3. DIFERENTES entre A e B (state_a != state_b nesse endereço)

Isso é uma condição muito mais rigorosa que reduz drasticamente os
falsos positivos causados por animações/física/timers, sobrando
principalmente candidatos ligados ao ESTADO (menu atual, seleção
etc), que só muda quando o usuário navega.

Usa numpy para comparação vetorizada — necessário para processar
~1GB de dados em segundos em vez de minutos.

Uso:
    python stable_scan.py <a1> <a2> <b1> <b2>

Onde:
    a1, a2 = dois snapshots tirados na MESMA tela A (parado)
    b1, b2 = dois snapshots tirados na MESMA tela B (parado)
"""

from __future__ import annotations

import sys

import numpy as np

import memory


def load_as_dict_np(name: str) -> dict[int, np.ndarray]:
    raw = memory.load_snapshot(name)
    return {base: np.frombuffer(data, dtype=np.uint8) for base, data in raw.items()}


def main() -> None:
    if len(sys.argv) != 5:
        print("Uso: python stable_scan.py <a1> <a2> <b1> <b2>")
        sys.exit(1)

    name_a1, name_a2, name_b1, name_b2 = sys.argv[1:5]

    print(f"[INFO] Carregando snapshots...")
    snap_a1 = load_as_dict_np(name_a1)
    snap_a2 = load_as_dict_np(name_a2)
    snap_b1 = load_as_dict_np(name_b1)
    snap_b2 = load_as_dict_np(name_b2)

    common_bases = (
        set(snap_a1) & set(snap_a2) & set(snap_b1) & set(snap_b2)
    )

    print(f"[INFO] {len(common_bases)} regiões presentes nos 4 snapshots.")

    stable_diff_addrs: list[tuple[int, int, bytes, bytes]] = []

    for base in sorted(common_bases):
        a1 = snap_a1[base]
        a2 = snap_a2[base]
        b1 = snap_b1[base]
        b2 = snap_b2[base]

        if not (len(a1) == len(a2) == len(b1) == len(b2)):
            continue

        stable_a = a1 == a2  # bool array: True onde NÃO mudou dentro de A
        stable_b = b1 == b2  # bool array: True onde NÃO mudou dentro de B
        diff_ab = a1 != b1   # bool array: True onde A difere de B

        candidate_mask = stable_a & stable_b & diff_ab

        if not candidate_mask.any():
            continue

        offsets = np.flatnonzero(candidate_mask)

        # agrupa offsets contíguos (ou quase) em blocos, igual ao
        # memory._diff_bytes, mas agora só sobre os offsets candidatos
        groups = _group_offsets(offsets, gap=2)

        for start, end in groups:
            old = a1[start:end].tobytes()
            new = b1[start:end].tobytes()
            stable_diff_addrs.append((base, start, old, new))

    print()
    print(f"[RESULT] {len(stable_diff_addrs)} candidatos "
          f"(estáveis em A, estáveis em B, diferentes entre A e B).")

    out_path = "stable_candidates.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        for base, offset, old, new in stable_diff_addrs:
            addr = base + offset
            line = _describe(addr, old, new)
            f.write(line + "\n")

    print(f"[INFO] Lista salva em {out_path}")
    print()

    # mostra os menores blocos primeiro (mais prováveis de ser um
    # único campo escalar: enum de tela, id, flag)
    small = [c for c in stable_diff_addrs if len(c[2]) <= 8]
    small.sort(key=lambda c: len(c[2]))

    print(f"[INFO] {len(small)} candidatos com bloco <= 8 bytes:")
    print()
    for base, offset, old, new in small[:80]:
        print("  " + _describe(base + offset, old, new))

    if len(small) > 80:
        print(f"  ... e mais {len(small) - 80} (veja {out_path})")


def _group_offsets(offsets: np.ndarray, gap: int) -> list[tuple[int, int]]:
    if len(offsets) == 0:
        return []

    groups = []
    start = offsets[0]
    prev = offsets[0]

    for o in offsets[1:]:
        if o - prev <= gap + 1:
            prev = o
            continue
        groups.append((int(start), int(prev) + 1))
        start = o
        prev = o

    groups.append((int(start), int(prev) + 1))
    return groups


def _describe(addr: int, old: bytes, new: bytes) -> str:
    import struct

    parts = [f"0x{addr:012X}", f"bytes: {old.hex()} -> {new.hex()}"]

    if len(old) == 4:
        oi = struct.unpack("<i", old)[0]
        ni = struct.unpack("<i", new)[0]
        parts.append(f"int32: {oi} -> {ni}")

    if len(old) == 1:
        parts.append(f"int8: {old[0]} -> {new[0]}")

    if len(old) == 2:
        oi = struct.unpack("<h", old)[0]
        ni = struct.unpack("<h", new)[0]
        parts.append(f"int16: {oi} -> {ni}")

    return " | ".join(parts)


if __name__ == "__main__":
    main()
