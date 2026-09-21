"""
Parseia um arquivo .CT (Cheat Engine Cheat Table, formato XML) e
extrai uma lista plana de todas as entradas com endereço/offsets,
para servir como ponto de partida documentado de ponteiros de memória
do FIFA 16 (em vez de redescobrir tudo via pointer scan do zero).

Uso:
    python parse_cheat_table.py <arquivo.CT>
"""

import sys
import xml.etree.ElementTree as ET


def walk_entries(entries_elem, path=()):
    """Percorre recursivamente <CheatEntries> produzindo uma lista de
    dicts com descrição, caminho hierárquico, endereço e offsets."""

    results = []

    for entry in entries_elem.findall("CheatEntry"):
        desc_elem = entry.find("Description")
        desc = desc_elem.text.strip('"') if desc_elem is not None and desc_elem.text else ""

        address_elem = entry.find("Address")
        address = address_elem.text if address_elem is not None else None

        offsets_elem = entry.find("Offsets")
        offsets = []
        if offsets_elem is not None:
            offsets = [off.text for off in offsets_elem.findall("Offset")]

        vartype_elem = entry.find("VariableType")
        vartype = vartype_elem.text if vartype_elem is not None else None

        current_path = path + (desc,)

        if address is not None:
            results.append(
                {
                    "path": " > ".join(current_path),
                    "description": desc,
                    "address": address,
                    "offsets": offsets,
                    "type": vartype,
                }
            )

        # recursão em sub-entradas (grupos)
        sub_entries = entry.find("CheatEntries")
        if sub_entries is not None:
            results.extend(walk_entries(sub_entries, current_path))

    return results


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "FIFA16_CT_v7.1.ct"

    tree = ET.parse(path)
    root = tree.getroot()

    top_entries = root.find("CheatEntries")
    all_entries = walk_entries(top_entries)

    print(f"Total de entradas com endereço: {len(all_entries)}\n")

    with open("cheat_table_parsed.txt", "w", encoding="utf-8") as f:
        for e in all_entries:
            f.write(f"[{e['path']}]\n")
            f.write(f"  address: {e['address']}\n")
            f.write(f"  offsets: {' -> '.join(e['offsets'])}\n")
            f.write(f"  type: {e['type']}\n\n")

    print("Salvo em cheat_table_parsed.txt")


if __name__ == "__main__":
    main()
