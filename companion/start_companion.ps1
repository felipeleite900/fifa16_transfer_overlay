# Inicia o FIFA 16 Companion completo:
#   - Electron (interface, escondida por padrao)
#   - Gamepad watcher (Python, monitora combo do controle em segundo plano)
#
# Uso:
#   .\start_companion.ps1
#
# Para parar, feche as duas janelas de console que serao abertas, ou
# use o Gerenciador de Tarefas (processos "electron.exe" e "python.exe").

$ErrorActionPreference = "Stop"

$companionDir = $PSScriptRoot
$pythonDir = Join-Path $companionDir "..\fifa_process_identifier"

# Garante que node.exe esteja no PATH desta sessão -- necessário
# porque electron.cmd invoca "node" internamente, e sessões abertas
# antes da instalação do Node.js podem não ter o PATH atualizado.
if ($env:Path -notlike "*nodejs*") {
    $env:Path += ";C:\Program Files\nodejs"
}

Write-Host "Iniciando FIFA 16 Companion..." -ForegroundColor Green

# Inicia o gamepad watcher em uma janela separada (para poder ver logs
# se precisar depurar).
Start-Process -FilePath "python" `
    -ArgumentList "-u", "gamepad_watcher.py" `
    -WorkingDirectory $pythonDir `
    -WindowStyle Minimized

# Inicia o Electron (main.js cuida de registrar o atalho de teclado e
# observar o sinal do gamepad watcher).
Start-Process -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -ArgumentList "start" `
    -WorkingDirectory $companionDir `
    -WindowStyle Minimized

Write-Host "Companion iniciado. Use Ctrl+Shift+P (teclado) ou L3+R3 (controle) para abrir/fechar." -ForegroundColor Green
