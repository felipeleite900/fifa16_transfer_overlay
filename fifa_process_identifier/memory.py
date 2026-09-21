"""
Enumeração, leitura e comparação de memória do processo do FIFA 16.

Escopo desta primeira versão (M1):
- enumerar regiões de memória PRIVADAS e COMMIT com permissão de escrita
  (é onde o estado dinâmico da UI/gameplay provavelmente vive — heap,
  variáveis globais alocadas em runtime etc). Regiões de código/DLLs
  mapeadas são ignoradas para reduzir ruído e volume de dados.
- ler os bytes dessas regiões (ReadProcessMemory);
- salvar um snapshot em disco (índice + dados brutos);
- comparar dois snapshots e reportar quais regiões/offsets mudaram.

Nada aqui escreve na memória do FIFA.
"""

from __future__ import annotations

import ctypes
import json
import struct
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# ------------------------------------------------------------------
# Constantes da API do Windows
# ------------------------------------------------------------------

MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000

PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

# Proteções que consideramos "graváveis" (candidatas a estado dinâmico)
WRITABLE_PROTECT = {
    0x04,  # PAGE_READWRITE
    0x08,  # PAGE_WRITECOPY
    0x40,  # PAGE_EXECUTE_READWRITE
    0x80,  # PAGE_EXECUTE_WRITECOPY
}

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

# Tamanho máximo de uma única região que aceitamos ler.
# Regiões maiores que isso normalmente são heaps genéricos enormes
# (ex: alocador de assets) e custariam caro para ler/comparar sem
# necessidade nesta fase inicial.
MAX_REGION_SIZE = 64 * 1024 * 1024  # 64 MB


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = wintypes.BOOL


# ------------------------------------------------------------------
# Enumeração de regiões
# ------------------------------------------------------------------

@dataclass
class Region:
    base: int
    size: int
    protect: int
    state: int
    type: int


def enumerate_regions(handle) -> list[Region]:
    """
    Percorre todo o espaço de endereçamento do processo usando
    VirtualQueryEx e retorna as regiões encontradas.
    """

    regions: list[Region] = []
    address = 0
    mbi = MEMORY_BASIC_INFORMATION()

    # Limite superior seguro (funciona tanto para processos 32 quanto
    # 64 bits; para 32 bits o VirtualQueryEx simplesmente vai parar de
    # retornar informação antes disso).
    max_address = 0x7FFFFFFF0000

    while address < max_address:
        result = VirtualQueryEx(
            handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)
        )

        if result == 0:
            break

        if mbi.RegionSize == 0:
            break

        regions.append(
            Region(
                base=mbi.BaseAddress or 0,
                size=mbi.RegionSize,
                protect=mbi.Protect,
                state=mbi.State,
                type=mbi.Type,
            )
        )

        address = (mbi.BaseAddress or 0) + mbi.RegionSize

    return regions


def filter_dynamic_regions(
    regions: list[Region], include_image: bool = False
) -> list[Region]:
    """
    Mantém apenas regiões comitadas e graváveis, candidatas a conter
    estado dinâmico (UI, gameplay, etc).

    Por padrão (include_image=False) mantém só regiões MEM_PRIVATE
    (heap dinâmico), igual à versão original.

    Com include_image=True, também inclui regiões MEM_IMAGE (seções
    de dados globais graváveis do próprio .exe/DLLs, tipo .data/.bss)
    — é onde variáveis globais simples como "current screen" tendem
    a morar, ao contrário de objetos alocados dinamicamente no heap.
    Continua excluindo código executável somente-leitura.
    """

    filtered = []
    allowed_types = {MEM_PRIVATE}
    if include_image:
        allowed_types.add(MEM_IMAGE)

    for region in regions:
        if region.state != MEM_COMMIT:
            continue
        if region.type not in allowed_types:
            continue
        if region.protect & PAGE_GUARD:
            continue
        if region.protect == PAGE_NOACCESS:
            continue
        if region.protect not in WRITABLE_PROTECT:
            continue
        if region.size > MAX_REGION_SIZE:
            continue

        filtered.append(region)

    return filtered


# ------------------------------------------------------------------
# Leitura de memória
# ------------------------------------------------------------------

def read_region(handle, region: Region) -> bytes | None:
    """
    Lê os bytes de uma região. Se a leitura falhar (ex: página
    protegida no meio do caminho), retorna None para essa região.
    """

    buffer = ctypes.create_string_buffer(region.size)
    bytes_read = ctypes.c_size_t(0)

    ok = ReadProcessMemory(
        handle,
        ctypes.c_void_p(region.base),
        buffer,
        region.size,
        ctypes.byref(bytes_read),
    )

    if not ok or bytes_read.value == 0:
        return None

    return buffer.raw[: bytes_read.value]


# ------------------------------------------------------------------
# Snapshots
# ------------------------------------------------------------------

def take_snapshot(handle, name: str, include_image: bool = False) -> Path:
    """
    Enumera as regiões dinâmicas do processo, lê seus bytes e salva
    em disco em snapshots/<name>/ (index.json + data.bin).

    include_image=True também captura regiões MEM_IMAGE graváveis
    (dados globais do .exe/DLLs) — ver filter_dynamic_regions.
    """

    snapshot_dir = SNAPSHOTS_DIR / name
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    regions = enumerate_regions(handle)
    regions = filter_dynamic_regions(regions, include_image=include_image)

    index = []
    data_path = snapshot_dir / "data.bin"

    read_count = 0
    skipped_count = 0

    with open(data_path, "wb") as data_file:
        offset = 0

        for region in regions:
            raw = read_region(handle, region)

            if raw is None:
                skipped_count += 1
                continue

            data_file.write(raw)

            index.append(
                {
                    "base": region.base,
                    "size": len(raw),
                    "offset": offset,
                    "protect": region.protect,
                }
            )

            offset += len(raw)
            read_count += 1

    with open(snapshot_dir / "index.json", "w", encoding="utf-8") as index_file:
        json.dump(index, index_file, indent=2)

    print(
        f"[SNAPSHOT] '{name}': {read_count} regiões lidas, "
        f"{skipped_count} ignoradas (falha de leitura)."
    )

    return snapshot_dir


def load_snapshot(name: str) -> dict[int, bytes]:
    """
    Carrega um snapshot salvo em disco e retorna um dicionário
    {base_address: bytes}.
    """

    snapshot_dir = SNAPSHOTS_DIR / name

    if not snapshot_dir.exists():
        raise FileNotFoundError(f"Snapshot '{name}' não encontrado.")

    with open(snapshot_dir / "index.json", "r", encoding="utf-8") as index_file:
        index = json.load(index_file)

    with open(snapshot_dir / "data.bin", "rb") as data_file:
        data = data_file.read()

    regions = {}

    for entry in index:
        start = entry["offset"]
        end = start + entry["size"]
        regions[entry["base"]] = data[start:end]

    return regions


# ------------------------------------------------------------------
# Diff entre snapshots
# ------------------------------------------------------------------

@dataclass
class Change:
    base: int
    offset: int
    old: bytes
    new: bytes

    @property
    def address(self) -> int:
        return self.base + self.offset

    def describe(self) -> str:
        old_i32 = _try_int32(self.old)
        new_i32 = _try_int32(self.new)
        old_f32 = _try_float32(self.old)
        new_f32 = _try_float32(self.new)

        parts = [f"0x{self.address:012X}"]
        parts.append(f"bytes: {self.old.hex()} -> {self.new.hex()}")

        if old_i32 is not None:
            parts.append(f"int32: {old_i32} -> {new_i32}")

        if old_f32 is not None:
            parts.append(f"float32: {old_f32:.4f} -> {new_f32:.4f}")

        return " | ".join(parts)


def _try_int32(b: bytes):
    if len(b) < 4:
        return None
    return struct.unpack_from("<i", b, 0)[0]


def _try_float32(b: bytes):
    if len(b) < 4:
        return None
    return struct.unpack_from("<f", b, 0)[0]


def diff_snapshots(name_a: str, name_b: str, context: int = 4) -> list[Change]:
    """
    Compara dois snapshots e retorna uma lista de mudanças
    (agrupadas em blocos contíguos de bytes diferentes), apenas
    para regiões presentes em ambos os snapshots no mesmo endereço
    base (a forma mais simples e confiável de comparar, já que o
    layout de memória pode variar entre execuções).
    """

    snap_a = load_snapshot(name_a)
    snap_b = load_snapshot(name_b)

    common_bases = sorted(set(snap_a.keys()) & set(snap_b.keys()))

    changes: list[Change] = []

    for base in common_bases:
        data_a = snap_a[base]
        data_b = snap_b[base]

        if len(data_a) != len(data_b):
            # Região existe nos dois, mas com tamanho diferente —
            # não comparamos byte a byte para evitar falso-positivo.
            continue

        if data_a == data_b:
            # Comparação nativa (C, muito rápida) — pula regiões
            # idênticas sem precisar entrar no loop byte a byte em
            # Python puro, que seria proibitivamente lento em
            # snapshots grandes.
            continue

        changes.extend(_diff_bytes(base, data_a, data_b, context))

    return changes


def _diff_bytes(base: int, a: bytes, b: bytes, context: int) -> list[Change]:
    """
    Encontra blocos contíguos de bytes diferentes entre dois buffers
    do mesmo tamanho, tolerando pequenos "gaps" de até `context`
    bytes iguais no meio de um bloco (útil para agrupar campos de uma
    mesma struct em uma única mudança em vez de várias fragmentadas).
    """

    changes = []
    length = len(a)
    i = 0

    while i < length:
        if a[i] != b[i]:
            start = i
            end = i + 1
            gap = 0

            while end < length:
                if a[end] != b[end]:
                    gap = 0
                    end += 1
                elif gap < context:
                    gap += 1
                    end += 1
                else:
                    break

                if end - start > 64:
                    # bloco já grande demais, provavelmente não é um
                    # único campo escalar — corta aqui.
                    break

            # remove eventual gap de bytes iguais no final do bloco
            while end > start and a[end - 1] == b[end - 1]:
                end -= 1

            changes.append(
                Change(base=base, offset=start, old=a[start:end], new=b[start:end])
            )

            i = end
        else:
            i += 1

    return changes


def list_snapshots() -> list[str]:
    if not SNAPSHOTS_DIR.exists():
        return []
    return sorted(p.name for p in SNAPSHOTS_DIR.iterdir() if p.is_dir())
