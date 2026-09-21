"""
Resolve uma cadeia de ponteiros no estilo Cheat Engine:

    fifa16.exe + base_offset -> [ptr] + offset1 -> [ptr] + offset2 -> ... -> valor final

Cada "offset" da cadeia (exceto o último) é somado ao endereço atual,
o resultado é lido como um ponteiro de 8 bytes (x64), e vira o
endereço atual do próximo passo. O último offset é somado e o valor
final é lido como int32 (ou outro tamanho, se pedido) — replica
exatamente a semântica do Cheat Engine ("Offsets" de baixo para cima
na UI = do endereço base em direção ao valor final).

Somente leitura (ReadProcessMemory). Não escreve nada.

Uso:
    python resolve_chain.py <base_offset_hex> <offset1_hex> <offset2_hex> ... [--size N] [--dump N] [--module NAME]

Exemplos:
    # Reactions (chain da Cheat Table): 034D7908 -> 5E8 -> 298 -> 0 -> E0 -> 120
    python resolve_chain.py 34D7908 5E8 298 0 E0 120

    # Mesma coisa, mas além do int32 final, despeja 256 bytes ao redor
    # do endereço final da struct (endereço ANTES de somar o último
    # offset) para inspecionar campos vizinhos:
    python resolve_chain.py 34D7908 5E8 298 0 E0 120 --dump 256

    # Usando fifa16.bin como módulo base em vez de fifa16.exe (jogos
    # protegidos por packer costumam ter o código real num .bin
    # separado, carregado em endereço diferente do .exe):
    python resolve_chain.py 34D7908 5E8 298 0 E0 120 --module fifa16.bin
"""

from __future__ import annotations

import ctypes
import struct
import sys

import modules
import process

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def read_bytes_at(handle, address: int, size: int) -> bytes | None:
    buffer = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)
    ok = ctypes.WinDLL("kernel32", use_last_error=True).ReadProcessMemory(
        handle,
        ctypes.c_void_p(address),
        buffer,
        size,
        ctypes.byref(bytes_read),
    )
    if not ok or bytes_read.value == 0:
        return None
    return buffer.raw[: bytes_read.value]


def read_ptr(handle, address: int) -> int | None:
    raw = read_bytes_at(handle, address, 8)
    if raw is None or len(raw) < 8:
        return None
    return int.from_bytes(raw, "little")


def resolve_chain(handle, base_address: int, offsets: list[int], verbose=True):
    """
    Segue a cadeia. Para todos os offsets menos o último, soma e
    dereferencia (lê ponteiro). Para o último offset, apenas soma
    (não dereferencia) — o chamador decide como ler o valor final.

    Retorna (endereco_final, trace) onde trace é a lista de endereços
    intermediários visitados (para debug).
    """
    trace = []
    current = base_address
    trace.append(("base", current))

    for i, off in enumerate(offsets[:-1]):
        addr_to_read = current + off
        ptr_value = read_ptr(handle, addr_to_read)
        if ptr_value is None:
            if verbose:
                print(f"[ERROR] Falha ao ler ponteiro em 0x{addr_to_read:012X} "
                      f"(passo {i}, offset +0x{off:X})")
            return None, trace
        trace.append((f"+0x{off:X} -> deref", addr_to_read, ptr_value))
        current = ptr_value

    final_address = current + offsets[-1]
    trace.append((f"+0x{offsets[-1]:X} (final, sem deref)", final_address))

    return final_address, trace


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    size = 4
    dump = 0
    module_name = "fifa16.exe"
    positional = []

    i = 0
    while i < len(args):
        if args[i] == "--size":
            size = int(args[i + 1])
            i += 2
        elif args[i] == "--dump":
            dump = int(args[i + 1])
            i += 2
        elif args[i] == "--module":
            module_name = args[i + 1]
            i += 2
        else:
            positional.append(args[i])
            i += 1

    if len(positional) < 2:
        print("Preciso de pelo menos base_offset e 1 offset.")
        sys.exit(1)

    base_offset = int(positional[0], 16)
    offsets = [int(x, 16) for x in positional[1:]]

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("[ERROR] FIFA 16 não está rodando.")
        sys.exit(1)

    handle = process.open_process(pid)
    mod_list = modules.list_modules(handle)
    exe_module = next(
        (m for m in mod_list if m.name.lower().endswith(module_name.lower())), None
    )
    if exe_module is None:
        print(f"[ERROR] Não encontrei {module_name} entre os módulos.")
        sys.exit(1)

    print(f"[INFO] {module_name} base = 0x{exe_module.base:012X}")
    base_address = exe_module.base + base_offset
    print(f"[INFO] Endereço base ({module_name}+0x{base_offset:X}) = 0x{base_address:012X}")

    final_address, trace = resolve_chain(handle, base_address, offsets)

    print()
    print("[TRACE]")
    for step in trace:
        print("    " + " ".join(str(x) if not isinstance(x, int) else f"0x{x:012X}" for x in step))

    if final_address is None:
        process.close_process(handle)
        sys.exit(1)

    print()
    print(f"[FINAL ADDRESS] 0x{final_address:012X}")

    raw = read_bytes_at(handle, final_address, max(size, dump))
    if raw is None:
        print("[ERROR] Falha ao ler o endereço final.")
        process.close_process(handle)
        sys.exit(1)

    if size == 4 and len(raw) >= 4:
        val_i32 = struct.unpack_from("<i", raw, 0)[0]
        val_f32 = struct.unpack_from("<f", raw, 0)[0]
        print(f"[VALUE] int32 = {val_i32}   float32 = {val_f32:.4f}   bytes = {raw[:4].hex()}")
    elif size == 1:
        print(f"[VALUE] byte = {raw[0]}")
    elif size == 8 and len(raw) >= 8:
        val_i64 = struct.unpack_from("<q", raw, 0)[0]
        print(f"[VALUE] int64 = {val_i64}   bytes = {raw[:8].hex()}")

    if dump:
        print()
        print(f"[DUMP] {dump} bytes a partir de 0x{final_address:012X}:")
        for row in range(0, len(raw), 16):
            chunk = raw[row:row + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            print(f"    +0x{row:03X}: {hex_part}")

    process.close_process(handle)


if __name__ == "__main__":
    main()
