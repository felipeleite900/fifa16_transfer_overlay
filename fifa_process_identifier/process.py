"""
Descoberta e abertura do processo do FIFA 16.

Responsabilidade única deste módulo:
- encontrar o PID do FIFA16.exe;
- abrir um handle de leitura (PROCESS_QUERY_INFORMATION | PROCESS_VM_READ);
- fechar o handle.

Nenhuma leitura de memória acontece aqui — isso fica em memory.py.
"""

from __future__ import annotations

import ctypes
import subprocess
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


def find_process_by_name(process_name: str) -> int | None:
    """
    Procura um processo pelo nome usando tasklist.

    Retorna:
        PID ou None
    """

    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    for line in result.stdout.splitlines():
        if process_name.lower() in line.lower():
            parts = line.split(",")

            if len(parts) >= 2:
                pid = parts[1].strip('"')
                return int(pid)

    return None


def open_process(pid: int) -> wintypes.HANDLE:
    """
    Abre o processo somente para consulta e leitura de memória.
    """

    access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ

    handle = OpenProcess(access, False, pid)

    if not handle:
        error = ctypes.get_last_error()
        raise RuntimeError(
            f"Não foi possível abrir o processo. Windows error: {error}"
        )

    return handle


def open_process_write(pid: int) -> wintypes.HANDLE:
    """
    Abre o processo para leitura E escrita de memória.

    Use com cautela — qualquer WriteProcessMemory pode corromper o
    estado do processo se o endereço/tamanho estiverem errados.
    """

    access = (
        PROCESS_QUERY_INFORMATION
        | PROCESS_VM_READ
        | PROCESS_VM_WRITE
        | PROCESS_VM_OPERATION
    )

    handle = OpenProcess(access, False, pid)

    if not handle:
        error = ctypes.get_last_error()
        raise RuntimeError(
            f"Não foi possível abrir o processo para escrita. Windows error: {error}"
        )

    return handle


def close_process(handle: wintypes.HANDLE) -> None:
    CloseHandle(handle)
