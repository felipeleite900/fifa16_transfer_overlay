# FIFA 16 Companion — Notas do Projeto

## Status atual (MVP v1 — funcional)

Pivotamos de "detecção automática de menu via memória" (ver seção
histórica abaixo) para uma abordagem pragmática que já entrega valor:

- **`fifa16_db_parser.py`** — parser de baixo nível do formato de
  banco de dados do FIFA 16 (t3db v8), usado tanto para o save
  (`DATA`) quanto para o banco estático do jogo (`fifa_ng_db.db`).
- **`fifa16_search.py`** — motor de busca de jogadores construído
  sobre o parser: localiza o save mais recente automaticamente,
  resolve nomes/nações/idade reais, e expõe filtros (posição, idade,
  overall, potencial, nacionalidade, pé preferido, nome).
- **`companion/`** — app Electron com interface de busca, que chama
  `fifa16_search.py` via subprocess. Abre/fecha via atalho de teclado
  (`Ctrl+Shift+P`) ou combo de controle (configurável).
- **`fifa_process_identifier/gamepad_watcher.py`** — monitor de
  controle via XInput (polling), detecta uma combinação de botões e
  sinaliza o Electron via arquivo (`gamepad_signal.txt`).

### Bugs corrigidos durante o desenvolvimento

1. **Encoding UTF-8**: a saída do `fifa16_search.py` via subprocess
   corrompia nomes acentuados (ex: "Mbappé" → "Mbapp?") porque o
   console/pipe do Windows usa um codepage não-UTF8 por padrão.
   Corrigido forçando `sys.stdout`/`stderr` para UTF-8 explicitamente.

2. **Nacionalidade errada (off-by-one)**: `fifa16_db_parser.load_metadata`
   indexava campos do XML de metadados só pelo `shortname` do campo
   (ex: "LEtt"), mas o mesmo shortname é reutilizado em tabelas
   diferentes com `rangelow` diferentes (ex: `nationid` tem
   `rangelow=1` na tabela `nations` mas `rangelow=0` em outra tabela).
   Isso causava um offset errado sendo aplicado. Corrigido indexando
   metadados por `(tabela, campo)` em vez de só `campo`.

3. **Idade calculada com data errada**: inicialmente calculávamos a
   idade dos jogadores usando a data real do sistema operacional.
   Isso está errado porque a carreira do FIFA tem seu próprio
   calendário interno, que pode estar anos à frente/atrás da data
   real (ex: um save observado estava ambientado em 2035). Corrigido
   lendo o campo `currdate` da tabela `GJUr` (formato `YYYYMMDD`) do
   próprio save e usando essa data como referência para o cálculo de
   idade, em vez de `date.today()`.

4. **`birthdate` decodificado**: campo de 20 bits, unidade = dias
   desde a época `1582-10-14` (dia seguinte à reforma do calendário
   Gregoriano). Validado comparando as datas de nascimento reais de
   Mbappé e Haaland com os valores brutos do save.

### Limitações conhecidas / decisões de escopo

- **Fullscreen exclusivo do FIFA**: o jogo roda em modo DirectX
  fullscreen exclusivo (confirmado pelo usuário — Alt+Tab causa
  troca de modo de vídeo). Isso significa que **não há overlay real**
  — abrir a janela do Companion tira o FIFA da tela cheia
  temporariamente (efeito aceito como comportamento do MVP). Overlay
  verdadeiro exigiria hook da swap chain do DirectX via DLL injection
  no processo do jogo — mesmo nível de esforço da "Fase 2" descartada
  abaixo.
- **Atalho de controle**: paddles traseiros do 8BitDo do usuário não
  emitem sinal XInput direto (nem em bits conhecidos nem
  desconhecidos) — o controle provavelmente precisa ser reconfigurado
  via app/firmware do fabricante para os paddles emularem outro botão.
  Testamos dois combos de botões frontais:
  - `LEFT_THUMB + RIGHT_THUMB` (L3+R3): **conflita** com um atalho
    nativo do próprio FIFA (o jogo reage ao mesmo combo).
  - `LEFT_THUMB + START`: aciona corretamente o toggle da janela, mas
    a transição de saída do fullscreen exclusivo não é instantânea —
    a primeira ativação começa a transição, e o estado "visível" da
    janela já é considerado true mesmo antes do efeito visual
    completar, exigindo às vezes um segundo toggle. Ainda não
    resolvido de forma robusta; aceito como limitação conhecida por
    ora. Possíveis melhorias futuras: delay/retry no `show()`, ou
    detectar a transição de fullscreen de alguma forma.
  - O atalho de **teclado** (`Ctrl+Shift+P`) tem o mesmo problema de
    transição de fullscreen, mas é o método mais confiável no momento.

### Arquivos de configuração gerados em runtime

- `fifa16_search_config.json` (raiz do projeto) — guarda o último
  save usado (path completo da pasta hash), para não perguntar toda
  vez qual save carregar.
- `fifa_process_identifier/gamepad_config.json` — combo de botões do
  controle e índice do controle (0-3). Editável manualmente.
- `fifa_process_identifier/gamepad_signal.txt` — arquivo de sinal
  (IPC simples) entre o watcher Python e o processo Electron.

### Como rodar

```powershell
# Inicia Electron + gamepad watcher juntos:
powershell -ExecutionPolicy Bypass -File companion\start_companion.ps1

# Ou individualmente, para debug:
cd companion; npm start                                    # Electron
python fifa_process_identifier\gamepad_watcher.py           # watcher
python fifa_process_identifier\gamepad_watcher.py --calibrate  # descobrir botões do controle
python fifa16_search.py --position ST --min-potential 85    # CLI direto
```

**Nota sobre PATH do Node.js**: sessões de terminal abertas antes da
instalação do Node podem não ter `C:\Program Files\nodejs` no PATH.
O `start_companion.ps1` já contorna isso automaticamente.

---

# Histórico: Investigação de Memória — FIFA 16 (M1)

> A seção abaixo documenta a tentativa original (descartada) de
> detectar automaticamente qual tela/menu do FIFA está ativa via
> leitura de memória do processo, antes do pivô para o MVP com
> hotkey manual descrito acima. Mantida para referência caso essa
> linha de investigação seja retomada no futuro.

Registro do que foi tentado/descoberto na tentativa de detectar
automaticamente qual tela/menu do FIFA 16 está ativa via leitura de
memória do processo. Guardado para retomar no futuro (possivelmente
via DLL injection / hook de código, que é bem mais robusto que ler
memória passivamente de fora).

## Status: PAUSADO — pivotado para MVP com hotkey manual

Não encontramos uma variável de memória estável e confiável que
represente "tela/menu atual". A causa provável: o FIFA 16 usa
Scaleform/Flash para UI, e o gerenciamento de estado de navegação
provavelmente vive em estruturas mais complexas (stack de telas,
sistema de eventos, containers dinâmicos gerenciados por índice) que
não são triviais de mapear só com leitura de memória — exigiria
disassembly do código (Ghidra/IDA) e/ou hook de função.

## Ambiente

- FIFA 16 é **64-bit** (`fifa16.exe`, machine type `0x8664`).
- Executável em `D:\Program Files\FIFA 16\fifa16.exe`.
- Módulo principal: `fifa16.exe` (base varia por execução devido a
  ASLR, tamanho ~0x9525000).
- Módulo de dados: `fifa16.bin` (carregado como módulo separado,
  tamanho ~0x9524000).
- Usuário roda um mod "FIFA Friends" com um servidor "CG Server" —
  **cuidado**: usar breakpoints de hardware / debug exceptions (ex:
  "Find out what accesses this address" do Cheat Engine) fez o jogo
  fechar abruptamente, possivelmente por conflito de debug registers
  ou detecção de anti-tamper do mod. Evitar técnicas de debugging
  ativo enquanto o mod estiver rodando; preferir leitura passiva
  (ReadProcessMemory) ou testar com o mod desligado.

## Ferramentas construídas (em `fifa_process_identifier/`)

- `process.py` — find/open/close do processo via PID (tasklist +
  OpenProcess/CloseHandle).
- `memory.py` — enumeração de regiões (VirtualQueryEx), leitura
  (ReadProcessMemory), snapshot em disco (index.json + data.bin),
  diff entre dois snapshots (por região/endereço).
  - `filter_dynamic_regions(regions, include_image=False)`: filtra
    regiões MEM_PRIVATE (heap) por padrão; com `include_image=True`
    também inclui MEM_IMAGE gravável (.data/.bss de exe/DLLs).
- `modules.py` — lista módulos carregados (EnumProcessModulesEx) e
  verifica se um endereço cai dentro de um módulo (útil para achar
  "âncoras" estáveis do tipo `modulo.exe+offset`).
- `pointer_scan.py` — dado um snapshot e uma string alvo, acha todas
  as ocorrências da string e todos os ponteiros de 8 bytes (x64) que
  apontam para perto dela (tolerância configurável).
- `pointer_bfs.py` / `pointer_bfs_addr.py` — pointer scan multi-nível
  (BFS): a cada nível, acha quem aponta para os alvos do nível
  anterior, verificando se algum ponteiro está dentro de um módulo
  (âncora estável). Versão `_addr` parte de um endereço específico
  em vez de uma string.
- `find_hub.py` — dado uma string alvo, acha "objetos hub" (endereços
  com muitas referências apontando para eles — fan-in alto),
  candidatos a singleton/estado importante.
- `stable_scan.py` — técnica de 4 estados (tipo Cheat Engine):
  compara 2 snapshots da tela A + 2 snapshots da tela B, mantendo só
  endereços estáveis dentro de cada tela mas diferentes entre elas.
- `watch_pointer.py` — observa ao vivo (polling) o conteúdo apontado
  por uma cadeia `modulo.exe+offset -> [ponteiro]`, extraindo texto
  legível.
- `analyze.py` — versão mais simples de diff com subtração de ruído
  (par a par, sem exigir estabilidade completa).

## Descobertas de dados (strings na memória)

O FIFA carrega dinamicamente (lazy-load, só aparecem depois de
visitar a tela pelo menos 1x na sessão) várias strings relacionadas à
UI Scaleform, incluindo:

- Nomes de ViewModel: `CareerHubViewModel`, `PlayerSearchViewModel`,
  `ClubsSearchViewModel`, `CareerCreationViewModel`,
  `CareerAutosaveViewModel`, `MainMenuMoviePlayerViewModel`, etc.
- Nomes de tela/transferência: `TransferPlayerSearch`,
  `EnterScoutReport`, `EnterHireScout`, `EnterHireScoutFromTransfers`,
  `EnterTransferOfferFromInbox`, `EnterPlayerSearchFromSelectNationality`,
  etc. (parecem nomes de eventos/funções de transição de estado).
- Arquivos de asset Scaleform: `game/components/CareerComponents/
  CareerHubWidget.swf`, `.../FluxTiles/career/FluxTile_*.swf`, etc.
- String de debug reveladora: `"GameMode[1]: Career : SubState((null))"`
  e `"GameMode[2]: CareerTraining"` — parecem ser strings de
  log/debug do motor mostrando o modo de jogo atual (não o menu de
  UI especificamente, mas pode valer a pena investigar mais — não
  aprofundamos nisso).

## Tentativas e resultados

### 1. Diff bruto de memória (Python, MEM_PRIVATE apenas)
- Snapshot A (tela 1) vs snapshot B (tela 2): ~279.000 mudanças.
- Ruído (mesma tela, só passa o tempo): ~120.000-365.000 mudanças.
- Conclusão: o motor do jogo está SEMPRE alterando muita memória em
  segundo plano (física, animação, áudio) mesmo parado em um menu.
  Diff bruto par-a-par não é seletivo o suficiente.

### 2. Stable scan (4 estados, Python com numpy)
- Comparando "estável em A" ∩ "estável em B" ∩ "diferente entre A e
  B": ainda ~95.000 candidatos. Reduz mas não converge o suficiente
  sozinho.

### 3. Cheat Engine — toggle scan manual (GUI)
- Sequência: Unknown initial → Changed (tela B) → Unchanged×2 (tela
  B parada) → repetir ciclo A/B várias vezes → Value between 0-200.
- Convergiu de 6 milhões → 1.561 candidatos. Mas 1.561 ainda é
  inviável de inspecionar manualmente item por item.
- **Restringir a MEM_PRIVATE + Writable** (desmarcar MEM_IMAGE/
  MEM_MAPPED nas Scan Settings) foi essencial para viabilizar o scan
  em tempo razoável.

### 4. Cheat Engine — "Find out what accesses this address"
- **CUIDADO**: usar essa feature na string `TransferPlayerSearch`
  (acessada com muita frequência, provavelmente a cada frame) causou
  o fechamento abrupto do FIFA. Suspeita: conflito com breakpoints
  de hardware do mod "FIFA Friends"/CG Server, ou detecção de
  debugger pelo anti-tamper do mod. Não tentar de novo com o mod
  ativo; se retomar, testar primeiro com o mod desligado.

### 5. Pointer scan de 1 nível (Python)
- Procurando ponteiros diretos (heap MEM_PRIVATE + MEM_IMAGE
  gravável) para as ocorrências de `TransferPlayerSearch`: achamos
  um "objeto hub" em `0x00002C6E4180` com 16 referências apontando
  para ele — forte candidato a singleton.
- BFS subiu 1 nível e achou uma âncora real:
  **`fifa16.exe+0x3357378` → aponta para `0x00002C6E4180`**
  (offset estável dentro do módulo, deveria sobreviver a ASLR entre
  execuções, contanto que a versão do exe não mude).

### 6. Watch ao vivo de `fifa16.exe+0x3357378`
- Resultado: **NÃO é o estado de tela**. É um buffer/log que recicla
  entre MUITOS widgets diferentes da mesma tela (FluxTile_DeadlineDay,
  FluxTile_StartingXI, FluxTile_ExtendedNews, EmailNotification,
  CareerHubWidget, FluxTile_Training...) — parece ser algo como
  "último asset/componente carregado ou atualizado", não
  especificamente a tela ativa. Fica girando entre os endereços
  `0x2C6E4040` a `0x2C6E4300` (buffer circular pequeno).
- Portanto essa âncora específica NÃO serve para detectar navegação
  de tela, mas a TÉCNICA (pointer BFS até achar offset em módulo)
  é válida e pode ser reaplicada em outro alvo.

### 7. Pointer scan multi-nível em CareerHubViewModel
- BFS de string até 5 níveis: não convergiu para nenhuma âncora em
  módulo (ficou em endereços de heap crescendo em ramificação a cada
  nível — sinal de estrutura muito conectada, tipo grafo, não uma
  cadeia linear simples).
- `find_hub.py` achou objeto hub em `0x00007FF5BED0` (8 referências)
  para `CareerHubViewModel`. BFS a partir desse endereço específico
  bateu em beco sem saída no nível 2 (nada aponta para os 8
  endereços do nível 1) — sugere que são elementos de um array/lista
  referenciados por índice, não por ponteiro individual direto.

## Hipóteses para investigação futura

1. **A string de debug `GameMode[N]: ...`** pode valer a pena seguir
   — parece ser gerada por um logger interno do motor que já
   descreve o estado (`Career`, `CareerTraining`, `SubState(...)`).
   Se существует uma flag/counter que dispara esse log, rastrear ela
   (ou o buffer de log em si, se for persistente) pode ser mais
   direto que perseguir ViewModels da UI.

2. **Ler a pilha de chamadas (call stack)** no momento da transição
   via inspeção passiva periódica (sem breakpoint) pode revelar o
   nome de função ativa via símbolos, mas exige achar/parsing de PDB
   ou fazer disassembly manual — escopo bem maior.

3. **DLL injection + hook de função** (ex: usando MinHook em C++/Rust)
   nas funções cujos nomes já conhecemos como strings (
   `EnterHireScoutFromTransfers`, `EnterScoutReport`, etc. — supondo
   que esses nomes correspondam a símbolos de função exportados ou
   próximos ao código que os referencia) seria a forma mais robusta
   de capturar o EVENTO de transição de tela, ao invés de tentar
   inferir o ESTADO via memória estática. Requer:
   - Localizar o código (não apenas a string) via disassembly
     (Ghidra/IDA) que referencia essas strings — normalmente há uma
     instrução `lea reg, [string]` perto da função relevante.
   - Implementar hook (inline hook/detour) nessa função.
   - Fazer em C++/Rust por questões de performance e estabilidade de
     hook (Python não é ideal para hooks de alta frequência).

4. **Testar sem o mod FIFA Friends/CG Server ativo** antes de tentar
   qualquer técnica de debugging ativo de novo (breakpoints,
   "find what accesses") — isso pode ter sido a causa do crash.

## Ferramentas reutilizáveis para retomar

Todos os scripts em `fifa_process_identifier/` continuam funcionais
e podem ser reaplicados a qualquer string/endereço novo:

```
python pointer_scan.py <snapshot> <string> [tolerancia]
python pointer_bfs.py <snapshot> <string> [max_levels] [tolerancia]
python pointer_bfs_addr.py <snapshot> <address_hex> [max_levels] [tolerancia]
python find_hub.py <snapshot> <string> [tolerancia]
python watch_pointer.py <offset_hex> [read_size]
python modules.py   # lista módulos carregados
```

Snapshots já capturados ficam em `snapshots/<nome>/` (podem estar
desatualizados se o jogo foi reiniciado — ASLR muda os endereços de
heap a cada execução, mas offsets de módulo (`fifa16.exe+offset`)
tendem a continuar válidos).
