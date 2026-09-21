"""
FIFA 16 Monitor - M1

Detecta o processo do FIFA 16, abre para leitura, e oferece um CLI
interativo para tirar snapshots de memória sob demanda e comparar
dois snapshots quaisquer.

Fluxo esperado de uso:

    1. Abra o FIFA 16 e deixe em uma tela conhecida (ex: Career Home).
    2. Rode este script.
    3. Digite um nome e pressione ENTER para tirar o snapshot 'A'.
    4. No FIFA, navegue até outra tela (ex: Transferências).
    5. Tire outro snapshot com outro nome ('B').
    6. Use o comando 'diff A B' para ver o que mudou na memória.

Nada aqui escreve na memória do FIFA nem no save.
"""

from __future__ import annotations

import sys
import time

import process
import memory

PROCESS_NAME = "FIFA16.exe"


def wait_for_fifa() -> int:
    print(f"[INFO] Procurando {PROCESS_NAME}...")

    while True:
        pid = process.find_process_by_name(PROCESS_NAME)

        if pid is not None:
            return pid

        print("[WAIT] FIFA 16 não encontrado.")
        time.sleep(2)


def cmd_snapshot(handle: int, name: str) -> None:
    if not name:
        print("[ERROR] Uso: snapshot <nome>")
        return

    print(f"[INFO] Capturando snapshot '{name}'... (pode levar alguns segundos)")
    memory.take_snapshot(handle, name)


def cmd_diff(args: list[str]) -> None:
    if len(args) != 2:
        print("[ERROR] Uso: diff <snapshot_a> <snapshot_b>")
        return

    name_a, name_b = args

    try:
        changes = memory.diff_snapshots(name_a, name_b)
    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
        return

    if not changes:
        print("[DIFF] Nenhuma mudança encontrada entre as regiões comuns.")
        return

    print(f"[DIFF] {len(changes)} mudanças encontradas:")
    print()

    for change in changes:
        print("  " + change.describe())


def cmd_list() -> None:
    snapshots = memory.list_snapshots()

    if not snapshots:
        print("[INFO] Nenhum snapshot salvo ainda.")
        return

    print("[INFO] Snapshots disponíveis:")
    for name in snapshots:
        print(f"  - {name}")


def print_help() -> None:
    print()
    print("Comandos disponíveis:")
    print("  snapshot <nome>        Captura um snapshot da memória atual")
    print("  diff <nome_a> <nome_b> Compara dois snapshots salvos")
    print("  list                   Lista snapshots salvos")
    print("  help                   Mostra esta ajuda")
    print("  exit                   Sai do programa")
    print()


def main() -> None:
    print("=" * 60)
    print(" FIFA 16 Monitor - M1")
    print("=" * 60)
    print()

    pid = wait_for_fifa()

    print()
    print("[FOUND] FIFA 16 encontrado!")
    print(f"[INFO] PID: {pid}")

    try:
        handle = process.open_process(pid)
    except RuntimeError as error:
        print(f"[ERROR] {error}")
        print(
            "[INFO] Tente executar o terminal como Administrador "
            "caso o Windows esteja bloqueando o acesso."
        )
        sys.exit(1)

    print("[OK] Processo aberto para leitura.")
    print_help()

    try:
        while True:
            current_pid = process.find_process_by_name(PROCESS_NAME)

            if current_pid is None:
                print("[INFO] FIFA 16 foi encerrado. Encerrando monitor.")
                break

            try:
                line = input("> ").strip()
            except EOFError:
                break

            if not line:
                continue

            parts = line.split()
            command = parts[0].lower()
            args = parts[1:]

            if command in ("exit", "quit"):
                break
            elif command == "help":
                print_help()
            elif command == "snapshot":
                cmd_snapshot(handle, args[0] if args else "")
            elif command == "diff":
                cmd_diff(args)
            elif command == "list":
                cmd_list()
            else:
                print(f"[ERROR] Comando desconhecido: {command}")
                print_help()
    finally:
        process.close_process(handle)
        print("[INFO] Handle fechado. Até mais.")


if __name__ == "__main__":
    main()
