"""
Monitor de controle (gamepad) via XInput, para acionar um atalho
global independente de qual janela está em foco (funciona mesmo com
o FIFA em fullscreen exclusivo, ao contrário de atalhos de teclado
do Electron que só cobrem o próprio processo).

Como funciona:
    - Faz polling do estado do controle via XInputGetState (API
      nativa do Windows, sem dependências externas).
    - Detecta quando uma combinação configurável de botões é
      pressionada simultaneamente (ex: LB+RB+Back).
    - Ao detectar, escreve um sinal em um arquivo (gamepad_signal.txt)
      que o processo Electron observa (fs.watch) e reage abrindo/
      fechando a janela da interface. Essa comunicação via arquivo é
      simples e evita a complexidade de expor uma porta/socket.

Modo de calibração:
    Muitos controles (incluindo 8BitDo com paddles traseiros) podem
    mapear botões extras de formas não óbvias dependendo do modo do
    controle. Rode com --calibrate para ver em tempo real quais bits
    são ativados ao pressionar cada botão, e descobrir o nome/código
    correto dos paddles para colocar no config.

Uso:
    python gamepad_watcher.py --calibrate      # modo de descoberta
    python gamepad_watcher.py                  # modo normal (usa config)
"""

from __future__ import annotations

import argparse
import ctypes
import json
import time
from ctypes import wintypes
from pathlib import Path

# ----------------------------------------------------------------------
# XInput API
# ----------------------------------------------------------------------

# Tenta a versão mais nova primeiro, cai para versões mais antigas se
# não existir (compatibilidade com Windows/drivers variados).
_XINPUT_DLL_NAMES = ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]

xinput = None
for dll_name in _XINPUT_DLL_NAMES:
    try:
        xinput = ctypes.WinDLL(dll_name)
        break
    except OSError:
        continue

if xinput is None:
    raise RuntimeError("Não foi possível carregar nenhuma versão de xinput*.dll")


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


XInputGetState = xinput.XInputGetState
XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
XInputGetState.restype = wintypes.DWORD

ERROR_SUCCESS = 0

# Mapa de bits conhecidos do wButtons (padrão XInput). Paddles de
# controles de terceiros (8BitDo, Scuf, etc.) geralmente são
# reprogramados PELO PRÓPRIO CONTROLE para emular um desses botões
# padrão (não existe um bit nativo de "paddle" no protocolo XInput) —
# por isso o modo --calibrate é importante: vai mostrar qual desses
# nomes acende quando você aperta o paddle.
BUTTON_BITS = {
    "DPAD_UP": 0x0001,
    "DPAD_DOWN": 0x0002,
    "DPAD_LEFT": 0x0004,
    "DPAD_RIGHT": 0x0008,
    "START": 0x0010,
    "BACK": 0x0020,
    "LEFT_THUMB": 0x0040,
    "RIGHT_THUMB": 0x0080,
    "LB": 0x0100,
    "RB": 0x0200,
    "A": 0x1000,
    "B": 0x2000,
    "X": 0x4000,
    "Y": 0x8000,
}

CONFIG_PATH = Path(__file__).parent / "gamepad_config.json"
SIGNAL_FILE = Path(__file__).parent / "gamepad_signal.txt"

DEFAULT_COMBO = ["LEFT_THUMB", "RIGHT_THUMB"]
POLL_INTERVAL_SECONDS = 0.05  # 20Hz, suficiente para detectar combos
DEBOUNCE_SECONDS = 0.6  # evita disparo repetido enquanto os botões
                         # continuam pressionados


def get_pressed_buttons(buttons_bitmask: int) -> set[str]:
    return {name for name, bit in BUTTON_BITS.items() if buttons_bitmask & bit}


def read_gamepad_state(controller_index: int = 0) -> XINPUT_GAMEPAD | None:
    state = XINPUT_STATE()
    result = XInputGetState(controller_index, ctypes.byref(state))
    if result != ERROR_SUCCESS:
        return None
    return state.Gamepad


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"combo": DEFAULT_COMBO, "controller_index": 0}


def save_default_config_if_missing() -> None:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps({"combo": DEFAULT_COMBO, "controller_index": 0}, indent=2),
            encoding="utf-8",
        )


def signal_toggle() -> None:
    # Inclui um timestamp de alta resolução para garantir que o
    # conteúdo do arquivo SEMPRE mude a cada sinal, mesmo que o
    # combo seja acionado repetidamente em sequência. Isso é
    # necessário porque o lado Electron detecta o sinal comparando o
    # conteúdo do arquivo com o valor anterior — se o conteúdo fosse
    # sempre a string fixa "toggle", uma segunda ativação seguida
    # não geraria uma mudança de conteúdo detectável.
    SIGNAL_FILE.write_text(f"toggle:{time.time_ns()}", encoding="utf-8")
    print("[SIGNAL] Combo detectado -> sinal 'toggle' enviado.")


# ----------------------------------------------------------------------
# Modo de calibração
# ----------------------------------------------------------------------

def find_connected_controllers() -> list[int]:
    connected = []
    for i in range(4):
        if read_gamepad_state(i) is not None:
            connected.append(i)
    return connected


def run_calibration(controller_index: int | None = 0) -> None:
    print("=" * 60)
    print(" Modo de calibração — pressione botões do controle")
    print(" (Ctrl+C para sair)")
    print("=" * 60)
    print()

    connected = find_connected_controllers()
    print(f"[INFO] Controles XInput detectados nos índices: {connected}")

    if not connected:
        print(
            "[WARN] Nenhum controle XInput detectado em nenhum dos 4 slots.\n"
            "       Isso pode significar que o 8BitDo está em um modo de\n"
            "       compatibilidade diferente de XInput (ex: modo DirectInput\n"
            "       puro, ou modo 'Switch'/'macOS'). Verifique o seletor de\n"
            "       modo físico do controle (geralmente combinação de botões\n"
            "       ou um switch) e tente colocá-lo em modo 'X' (Xbox/XInput)."
        )
        return

    if controller_index not in connected:
        controller_index = connected[0]
        print(f"[INFO] Usando índice {controller_index} (primeiro conectado).")

    print()
    print("Pressione qualquer botão, incluindo os paddles traseiros.")
    print("O valor bruto (raw) do wButtons também é mostrado em hex,")
    print("caso o paddle não corresponda a nenhum nome conhecido.")
    print()

    last_pressed: set[str] = set()
    last_raw = None

    try:
        while True:
            gamepad = read_gamepad_state(controller_index)

            if gamepad is None:
                print(f"[WARN] Controle {controller_index} desconectado.")
                time.sleep(1)
                continue

            pressed = get_pressed_buttons(gamepad.wButtons)
            raw = gamepad.wButtons

            if pressed != last_pressed or raw != last_raw:
                extra = ""
                unknown_bits = raw & ~sum(BUTTON_BITS.values())
                if unknown_bits:
                    extra = f"  [bits desconhecidos: 0x{unknown_bits:04X}]"
                label = sorted(pressed) if pressed else "(nenhum botão mapeado)"
                print(f"raw=0x{raw:04X}  botões={label}{extra}")
                last_pressed = pressed
                last_raw = raw

            if gamepad.bLeftTrigger > 20 or gamepad.bRightTrigger > 20:
                print(
                    f"  triggers: L={gamepad.bLeftTrigger} R={gamepad.bRightTrigger}"
                )

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n[INFO] Calibração encerrada.")


# ----------------------------------------------------------------------
# Modo normal (watcher)
# ----------------------------------------------------------------------

def run_watcher() -> None:
    save_default_config_if_missing()
    config = load_config()
    combo = set(config.get("combo", DEFAULT_COMBO))
    controller_index = config.get("controller_index", 0)

    print("=" * 60)
    print(" FIFA 16 Companion — Gamepad Watcher")
    print("=" * 60)
    print(f"[INFO] Combo configurado: {sorted(combo)}")
    print(f"[INFO] Controle: índice {controller_index}")
    print(f"[INFO] Arquivo de sinal: {SIGNAL_FILE}")
    print("[INFO] Pressione Ctrl+C para parar.")
    print()

    last_combo_active = False
    last_trigger_time = 0.0

    try:
        while True:
            gamepad = read_gamepad_state(controller_index)

            if gamepad is None:
                time.sleep(0.5)
                continue

            pressed = get_pressed_buttons(gamepad.wButtons)
            combo_active = combo.issubset(pressed)

            now = time.time()

            if (
                combo_active
                and not last_combo_active
                and (now - last_trigger_time) > DEBOUNCE_SECONDS
            ):
                signal_toggle()
                last_trigger_time = now

            last_combo_active = combo_active

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n[INFO] Watcher encerrado.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--calibrate",
        action="store_true",
        help="Modo de calibração: mostra botões pressionados em tempo real",
    )
    ap.add_argument("--controller-index", type=int, default=0)
    args = ap.parse_args()

    if args.calibrate:
        run_calibration(args.controller_index)
    else:
        run_watcher()


if __name__ == "__main__":
    main()
