"""
Teste de escrita real na memoria do FIFA 16: altera um unico campo
(strength) de um jogador especifico (Ibrahim Mbaye, playerid 74449)
diretamente na tabela CZUM residente em RAM, sem precisar de nenhuma
tela especifica aberta no jogo.

Uso:
    python test_memory_write.py write <novo_valor>
    python test_memory_write.py revert <valor_original>
    python test_memory_write.py read
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

import process
import memory

sys.path.insert(0, str(Path(__file__).parent.parent))
import fifa16_db_parser as p

sys.stdout.reconfigure(encoding="utf-8")

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
WriteProcessMemory.restype = wintypes.BOOL

TARGET_PLAYER_ID = int(sys.argv[3]) if len(sys.argv) > 3 else 74449  # default: Ibrahim Mbaye
FIELD_NAME = sys.argv[4] if len(sys.argv) > 4 else "strength"

# Regiao onde encontramos a database de jogadores (descoberta nesta sessao)
DB_REGION_BASE = 0x00008BE70000
DB_REGION_SIZE = 0xE00000
DB_SIGNATURE = b"DB\x00\x08\x00\x00\x00\x00"


def locate_field():
    """Le a regiao, parseia o header da tabela CZUM, encontra o registro
    do jogador alvo e retorna (record_absolute_addr, field, record_bytes)."""

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process_write(pid)

    buf = ctypes.create_string_buffer(DB_REGION_SIZE)
    bytes_read = ctypes.c_size_t(0)
    ok = memory.ReadProcessMemory(
        handle,
        ctypes.c_void_p(DB_REGION_BASE),
        buf,
        DB_REGION_SIZE,
        ctypes.byref(bytes_read),
    )
    if not ok:
        print("[ERROR] Falha ao ler a região de memória.")
        sys.exit(1)

    data = buf.raw[: bytes_read.value]

    # localiza dinamicamente o offset da assinatura de database dentro
    # da regiao (o offset relativo pode variar entre execucoes/tempo,
    # mesmo que a regiao base seja a mesma)
    db_offsets = p.find_databases(data)
    db_offset_in_region = None
    for off in db_offsets:
        try:
            candidate_db = p.parse_database(data, off)
            if any(t.short_name == "CZUM" for t in candidate_db["tables"]):
                db_offset_in_region = off
                break
        except Exception:
            continue

    if db_offset_in_region is None:
        print("[ERROR] Não encontrei a tabela CZUM em nenhuma assinatura de database nesta região.")
        sys.exit(1)

    metadata = p.load_metadata(Path(r"D:\Program Files\FIFA 16\data\db\fifa_ng_db-meta.xml"))
    db = p.parse_database(data, db_offset_in_region, metadata)
    czum = next(t for t in db["tables"] if t.short_name == "CZUM")

    field = next(f for f in czum.fields if f.name == FIELD_NAME or f.short_name == FIELD_NAME)

    records_start = czum.offset + 36 + czum.field_count * 16

    # encontra o indice do registro do jogador alvo procurando o campo playerid
    playerid_field = next(f for f in czum.fields if f.name == "playerid" or f.short_name == "playerid")

    found_index = None
    for i in range(czum.written_record_count):
        rp = records_start + i * czum.record_size
        raw_pid = p.read_packed_int(
            data[rp : rp + czum.record_size], playerid_field.bit_offset, playerid_field.depth
        )
        if playerid_field.range_low:
            raw_pid += playerid_field.range_low
        if raw_pid == TARGET_PLAYER_ID:
            found_index = i
            break

    if found_index is None:
        print(f"[ERROR] Jogador {TARGET_PLAYER_ID} não encontrado na tabela.")
        sys.exit(1)

    record_offset_in_region = records_start + found_index * czum.record_size
    record_abs_addr = DB_REGION_BASE + record_offset_in_region
    record_bytes = data[record_offset_in_region : record_offset_in_region + czum.record_size]

    return handle, record_abs_addr, field, bytearray(record_bytes)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    handle, record_abs_addr, field, record_bytes = locate_field()

    current_value = p.read_packed_int(bytes(record_bytes), field.bit_offset, field.depth)
    if field.range_low:
        current_value += field.range_low

    print(f"[INFO] Registro do jogador em memória: 0x{record_abs_addr:012X}")
    print(f"[INFO] Campo '{FIELD_NAME}': bit_offset={field.bit_offset} depth={field.depth} "
          f"range_low={field.range_low}")
    print(f"[INFO] Valor atual de '{FIELD_NAME}': {current_value}")

    if action == "read":
        process.close_process(handle)
        return

    if action in ("write", "revert"):
        if len(sys.argv) < 3:
            print("Preciso do novo valor.")
            process.close_process(handle)
            sys.exit(1)

        new_value = int(sys.argv[2])
        raw_value = new_value - (field.range_low or 0)

        p.write_packed_int(record_bytes, field.bit_offset, field.depth, raw_value)

        bytes_written = ctypes.c_size_t(0)
        buf_to_write = bytes(record_bytes)
        ok = WriteProcessMemory(
            handle,
            ctypes.c_void_p(record_abs_addr),
            buf_to_write,
            len(buf_to_write),
            ctypes.byref(bytes_written),
        )

        if not ok:
            error = ctypes.get_last_error()
            print(f"[ERROR] WriteProcessMemory falhou. Windows error: {error}")
        else:
            print(f"[OK] Escrito {bytes_written.value} bytes. "
                  f"Novo valor de '{FIELD_NAME}' deve ser {new_value}.")

    process.close_process(handle)


if __name__ == "__main__":
    main()
