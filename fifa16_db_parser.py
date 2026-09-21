#!/usr/bin/env python3
"""
Minimal FIFA t3db v8 reader for FIFA 16 career/save DATA files.

Current scope:
- locate embedded FIFA databases in a DATA file
- parse database header + table directory
- parse table headers + field descriptors
- decode raw integer/float/fixed-string/Huffman-string fields
- optionally enrich tables/fields from fifa_ng_db-meta.xml
- export decoded databases to JSON

This is intentionally read-only. Do not use it to overwrite a real save yet.
"""

from __future__ import annotations
import argparse
import json
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path

DB_SIGNATURE = b"DB\x00\x08\x00\x00\x00\x00"


def u8(b, p): return b[p]
def u16(b, p): return struct.unpack_from("<H", b, p)[0]
def i16(b, p): return struct.unpack_from("<h", b, p)[0]
def u32(b, p): return struct.unpack_from("<I", b, p)[0]
def i32(b, p): return struct.unpack_from("<i", b, p)[0]
def f32(b, p): return struct.unpack_from("<f", b, p)[0]


@dataclass
class Field:
    short_name: str
    storage_type: int
    bit_offset: int
    depth: int
    name: str | None = None
    xml_type: str | None = None
    range_low: int | None = None
    range_high: int | None = None


@dataclass
class Table:
    short_name: str
    relative_offset: int
    offset: int
    record_size: int
    record_bit_length: int
    compressed_string_length: int
    record_count: int
    written_record_count: int
    cancelled_record_count: int
    field_count: int
    fields: list[Field]


def load_metadata(path: Path | None):
    """
    Carrega metadados de tabelas/campos do fifa_ng_db-meta.xml.

    IMPORTANTE: o mesmo `shortname` de campo (ex: "LEtt") pode
    aparecer em múltiplas tabelas com significados/ranges DIFERENTES
    (ex: nationid tem rangelow=1 na tabela "nations" mas rangelow=0
    em outra tabela). Por isso os campos são indexados por
    (table_shortname, field_shortname), não apenas pelo shortname do
    campo isoladamente — indexar só pelo campo causava valores de
    range_low errados sendo aplicados (bug encontrado: nacionalidade
    de jogadores saindo com off-by-one, ex: Mbappé resolvendo para
    "FYR Macedonia" em vez de "France").

    Mantemos também um índice global (fields_by_shortname_only) como
    fallback para compatibilidade, mas ele não deve ser usado quando
    já sabemos a tabela.
    """
    if not path:
        return {}, {}, {}
    root = ET.parse(path).getroot()
    tables = {}
    fields_by_table = {}
    fields_global = {}
    for t in root.findall(".//table"):
        ts = t.get("shortname")
        if not ts:
            continue
        tables[ts] = t.get("name")
        for f in t.findall("./fields/field"):
            fs = f.get("shortname")
            if fs:
                meta = {
                    "name": f.get("name"),
                    "type": f.get("type"),
                    "range_low": int(f.get("rangelow", "0")),
                    "range_high": int(f.get("rangehigh", "0")),
                }
                fields_by_table[(ts, fs)] = meta
                # fallback global: só define se ainda não existir,
                # para não sobrescrever com ranges de outra tabela
                fields_global.setdefault(fs, meta)
    return tables, fields_global, fields_by_table


def find_databases(data: bytes):
    return [i for i in range(len(data)) if data.startswith(DB_SIGNATURE, i)]


def parse_database(data: bytes, start: int, metadata=None):
    declared_size = u32(data, start + 8)
    table_count = u32(data, start + 16)
    directory_end = 24 + table_count * 8
    table_data_base = directory_end + 4

    directory = []
    for i in range(table_count):
        p = start + 24 + i * 8
        short = data[p:p+4].decode("latin1")
        rel = u32(data, p + 4)
        directory.append((short, rel))

    tables = []
    for i, (short, rel) in enumerate(directory):
        off = start + table_data_base + rel
        end = start + (declared_size if i + 1 == table_count
                       else table_data_base + directory[i + 1][1])

        record_size = u32(data, off + 4)
        record_bits = u32(data, off + 8)
        compressed_len = u32(data, off + 12)
        record_count = u16(data, off + 16)
        written_count = u16(data, off + 18)
        cancelled_count = u16(data, off + 20)
        field_count = u8(data, off + 24)

        fields = []
        for j in range(field_count):
            p = off + 36 + j * 16
            storage_type = u32(data, p)
            bit_offset = u32(data, p + 4)
            field_short = data[p+8:p+12].decode("latin1")
            depth = u32(data, p + 12)
            meta = {}
            if metadata:
                fields_by_table = metadata[2] if len(metadata) > 2 else {}
                meta = (
                    fields_by_table.get((short, field_short))
                    or metadata[1].get(field_short)
                    or {}
                )
            fields.append(Field(
                short_name=field_short,
                storage_type=storage_type,
                bit_offset=bit_offset,
                depth=depth,
                name=meta.get("name"),
                xml_type=meta.get("type"),
                range_low=meta.get("range_low"),
                range_high=meta.get("range_high"),
            ))

        tables.append(Table(
            short_name=short,
            relative_offset=rel,
            offset=off,
            record_size=record_size,
            record_bit_length=record_bits,
            compressed_string_length=compressed_len,
            record_count=record_count,
            written_record_count=written_count,
            cancelled_record_count=cancelled_count,
            field_count=field_count,
            fields=fields,
        ))

    return {
        "offset": start,
        "declared_size": declared_size,
        "table_count": table_count,
        "tables": tables,
    }


def read_packed_int(record: bytes, bit_offset: int, depth: int) -> int:
    shift = bit_offset % 8
    first = bit_offset // 8
    count = (shift + depth + 7) // 8
    packed = 0
    for i in range(count - 1, -1, -1):
        packed = packed * 256 + record[first + i]
    return (packed >> shift) & ((1 << depth) - 1)


def write_packed_int(record: bytearray, bit_offset: int, depth: int, value: int) -> None:
    """
    Escreve `value` (já sem aplicar range_low -- ver nota abaixo) nos
    bits [bit_offset, bit_offset+depth) de `record`, preservando todos
    os outros bits ao redor (inclusive bits de outros campos que podem
    compartilhar os mesmos bytes, já que os campos não são
    necessariamente alinhados a byte).

    Espelha exatamente a lógica de `read_packed_int`: mesmo cálculo de
    `shift`/`first`/`count`, mas em vez de só extrair os bits, lê os
    bytes atuais, limpa a região do campo com uma máscara, insere o
    novo valor, e escreve de volta.

    IMPORTANTE: `value` deve ser o valor BRUTO a gravar (ou seja, se o
    campo tem `range_low` na metadata, o chamador deve subtrair esse
    range_low antes de chamar esta função — o range_low é aplicado na
    LEITURA como `value += range_low`, então a escrita deve fazer o
    inverso: `raw = value - range_low`). Esta função não tem acesso à
    metadata, então não faz essa conversão sozinha.

    `record` deve ser um `bytearray` (mutável), não `bytes`.
    """
    if value < 0 or value >= (1 << depth):
        raise ValueError(
            f"Valor {value} não cabe em {depth} bits (máximo {(1 << depth) - 1})"
        )

    shift = bit_offset % 8
    first = bit_offset // 8
    count = (shift + depth + 7) // 8

    # lê os bytes atuais na mesma ordem/convenção de read_packed_int
    packed = 0
    for i in range(count - 1, -1, -1):
        packed = packed * 256 + record[first + i]

    # máscara dos bits do campo dentro do inteiro "packed" de `count` bytes
    field_mask = ((1 << depth) - 1) << shift

    packed = (packed & ~field_mask) | ((value << shift) & field_mask)

    # escreve de volta, byte a byte, little-endian (mesma convenção de leitura)
    for i in range(count):
        record[first + i] = packed & 0xFF
        packed >>= 8


def decode_huffman(block: bytes, pointer: int, storage_type: int):
    if pointer == -1:
        return ""
    if pointer < 0 or pointer >= len(block):
        return None

    first_string_offset = None
    # The first non-negative pointer is the start of the payload after the tree.
    # Callers pass the whole compressed block and pointer; infer the tree end
    # from the smallest non-negative pointer at table level.
    return None


def decode_table(data: bytes, table: Table):
    rows = []
    records_start = table.offset + 36 + table.field_count * 16
    compressed_start = records_start + table.written_record_count * table.record_size
    compressed_end = compressed_start + table.compressed_string_length

    # Huffman tree boundary = smallest non-negative pointer among string fields.
    pointers = []
    if table.compressed_string_length:
        for i in range(table.written_record_count):
            rp = records_start + i * table.record_size
            for f in table.fields:
                if f.storage_type in (13, 14):
                    pointers.append(i32(data, rp + f.bit_offset // 8))
    first_ptr = min((p for p in pointers if p >= 0), default=0)
    nodes = []
    for p in range(0, first_ptr, 4):
        nodes.append((u8(data, compressed_start+p),
                      u8(data, compressed_start+p+1),
                      u8(data, compressed_start+p+2),
                      u8(data, compressed_start+p+3)))

    def huff(ptr, typ):
        if ptr == -1:
            return ""
        cur = compressed_start + ptr
        length = u8(data, cur) if typ == 13 else struct.unpack_from(">H", data, cur)[0]
        cur += 1 if typ == 13 else 2
        if not nodes:
            return data[cur:cur+length].decode("utf-8", errors="replace")

        out = bytearray()
        node = 0
        while len(out) < length:
            byte = u8(data, cur); cur += 1
            for bitpos in range(7, -1, -1):
                if len(out) >= length:
                    break
                child0, leaf0, child1, leaf1 = nodes[node]
                bit = (byte >> bitpos) & 1
                child = child0 if bit == 0 else child1
                leaf = leaf0 if bit == 0 else leaf1
                if child == 0:
                    out.append(leaf)
                    node = 0
                else:
                    node = child
        return bytes(out).decode("utf-8", errors="replace")

    for i in range(table.written_record_count):
        rp = records_start + i * table.record_size
        if data[rp + table.record_size - 1] & 0x80:
            continue
        row = {}
        for f in sorted(table.fields, key=lambda x: x.bit_offset):
            key = f.name or f.short_name
            if f.storage_type == 0:
                start = rp + f.bit_offset // 8
                raw = data[start:start + f.depth // 8]
                value = raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")
            elif f.storage_type == 3:
                value = read_packed_int(data[rp:rp+table.record_size], f.bit_offset, f.depth)
                if f.range_low is not None:
                    value += f.range_low
            elif f.storage_type == 4:
                value = f32(data, rp + f.bit_offset // 8)
            elif f.storage_type in (13, 14):
                value = huff(i32(data, rp + f.bit_offset // 8), f.storage_type)
            else:
                value = None
            row[key] = value
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--metadata")
    ap.add_argument("--json", default="fifa16_decoded.json")
    ap.add_argument("--decode", action="store_true")
    args = ap.parse_args()

    raw = Path(args.data).read_bytes()
    metadata = load_metadata(Path(args.metadata)) if args.metadata else ({}, {}, {})
    offsets = find_databases(raw)

    result = []
    for db_index, off in enumerate(offsets, 1):
        db = parse_database(raw, off, metadata)
        db["database_index"] = db_index
        db["tables"] = [asdict(t) for t in db["tables"]]
        if args.decode:
            for tdict, t in zip(db["tables"], parse_database(raw, off, metadata)["tables"]):
                tdict["rows"] = decode_table(raw, t)
        result.append(db)

    Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Found {len(result)} embedded databases")
    for db in result:
        print(f"DB {db['database_index']}: offset={db['offset']:,} size={db['declared_size']:,} tables={db['table_count']}")
        for t in db["tables"]:
            name = t.get("short_name")
            print(f"  {name}: rows={t['written_record_count']:,} fields={t['field_count']}")


if __name__ == "__main__":
    main()
