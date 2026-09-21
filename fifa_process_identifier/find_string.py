"""
Localiza uma string (bytes) dentro de um snapshot e traduz a posição
no arquivo data.bin de volta para o endereço real de memória do
processo, usando o index.json.

Uso:
    python find_string.py <snapshot_name> <needle>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: python find_string.py <snapshot_name> <needle>")
        sys.exit(1)

    name, needle = sys.argv[1], sys.argv[2].encode()

    snapshot_dir = SNAPSHOTS_DIR / name

    with open(snapshot_dir / "index.json", "r", encoding="utf-8") as f:
        index = json.load(f)

    with open(snapshot_dir / "data.bin", "rb") as f:
        data = f.read()

    start = 0
    found_any = False

    while True:
        pos = data.find(needle, start)
        if pos == -1:
            break

        found_any = True

        # encontra a região que contém essa posição
        for entry in index:
            file_start = entry["offset"]
            file_end = file_start + entry["size"]

            if file_start <= pos < file_end:
                addr = entry["base"] + (pos - file_start)
                print(
                    f"file_offset={pos:#x}  ->  "
                    f"region_base=0x{entry['base']:012X}  "
                    f"addr=0x{addr:012X}  "
                    f"region_offset={pos - file_start:#x}"
                )
                break
        else:
            print(f"file_offset={pos:#x} -> (não encontrado em nenhuma região?!)")

        start = pos + 1

    if not found_any:
        print("Não encontrado.")


if __name__ == "__main__":
    main()
