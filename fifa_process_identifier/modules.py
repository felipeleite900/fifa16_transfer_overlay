"""
Enumeração de módulos carregados (fifa16.exe e DLLs) no processo.

Usado para verificar se um endereço de memória cai dentro da faixa de
um módulo — módulos são carregados em endereços que (com ASLR à
parte) tendem a ser mais previsíveis/estáveis entre execuções do que
alocações de heap, e frequentemente contêm variáveis globais/estáticas
usadas como "âncoras" para pointer chains.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

psapi = ctypes.WinDLL("psapi", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

LIST_MODULES_ALL = 0x03


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wintypes.DWORD),
        ("EntryPoint", ctypes.c_void_p),
    ]


EnumProcessModulesEx = psapi.EnumProcessModulesEx
EnumProcessModulesEx.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.HMODULE),
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.DWORD,
]
EnumProcessModulesEx.restype = wintypes.BOOL

GetModuleFileNameExW = psapi.GetModuleFileNameExW
GetModuleFileNameExW.argtypes = [
    wintypes.HANDLE,
    wintypes.HMODULE,
    wintypes.LPWSTR,
    wintypes.DWORD,
]
GetModuleFileNameExW.restype = wintypes.DWORD

GetModuleInformation = psapi.GetModuleInformation
GetModuleInformation.argtypes = [
    wintypes.HANDLE,
    wintypes.HMODULE,
    ctypes.POINTER(MODULEINFO),
    wintypes.DWORD,
]
GetModuleInformation.restype = wintypes.BOOL


@dataclass
class Module:
    name: str
    base: int
    size: int

    @property
    def end(self) -> int:
        return self.base + self.size

    def contains(self, address: int) -> bool:
        return self.base <= address < self.end

    def offset_of(self, address: int) -> int:
        return address - self.base


def list_modules(handle) -> list[Module]:
    """
    Lista todos os módulos (exe + DLLs) carregados no processo.
    Requer um handle aberto com PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    (o mesmo que já usamos em process.open_process).
    """

    needed = wintypes.DWORD(0)
    # primeira chamada só para descobrir o tamanho necessário
    buf_count = 1024
    while True:
        arr_type = wintypes.HMODULE * buf_count
        modules_arr = arr_type()

        ok = EnumProcessModulesEx(
            handle,
            modules_arr,
            ctypes.sizeof(modules_arr),
            ctypes.byref(needed),
            LIST_MODULES_ALL,
        )

        if not ok:
            error = ctypes.get_last_error()
            raise RuntimeError(f"EnumProcessModulesEx falhou: {error}")

        count = needed.value // ctypes.sizeof(wintypes.HMODULE)

        if count <= buf_count:
            break

        buf_count = count  # buffer pequeno demais, tenta de novo maior

    modules = []

    for i in range(count):
        hmodule = modules_arr[i]

        name_buf = ctypes.create_unicode_buffer(260)
        GetModuleFileNameExW(handle, hmodule, name_buf, 260)

        info = MODULEINFO()
        GetModuleInformation(handle, hmodule, ctypes.byref(info), ctypes.sizeof(info))

        modules.append(
            Module(
                name=name_buf.value,
                base=info.lpBaseOfDll or 0,
                size=info.SizeOfImage,
            )
        )

    return modules


def find_module_for_address(modules: list[Module], address: int) -> Module | None:
    for m in modules:
        if m.contains(address):
            return m
    return None


if __name__ == "__main__":
    import process

    pid = process.find_process_by_name("FIFA16.exe")
    if pid is None:
        print("FIFA 16 não encontrado.")
    else:
        handle = process.open_process(pid)
        mods = list_modules(handle)
        process.close_process(handle)

        print(f"[INFO] {len(mods)} módulos encontrados:")
        for m in sorted(mods, key=lambda x: x.base):
            print(f"  0x{m.base:012X} - 0x{m.end:012X}  size=0x{m.size:08X}  {m.name}")
