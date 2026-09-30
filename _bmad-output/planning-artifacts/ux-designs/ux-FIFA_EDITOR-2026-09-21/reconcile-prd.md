---
title: Reconciliação PRD × UX — Central de Scout
created: 2026-09-21
sources:
  - "{planning_artifacts}/prds/prd-FIFA_EDITOR-2026-09-21/prd.md"
  - "{planning_artifacts}/ux-designs/ux-FIFA_EDITOR-2026-09-21/DESIGN.md"
  - "{planning_artifacts}/ux-designs/ux-FIFA_EDITOR-2026-09-21/EXPERIENCE.md"
---

# Reconciliação PRD × UX — Central de Scout

Comparação do `prd.md` contra `DESIGN.md`/`EXPERIENCE.md`, cobrindo os 11 FRs,
as 3 UJs, consistência de Glossário, e captura de intenção qualitativa
(tom/voz/feel). 7 gaps encontrados — nenhum bloqueante para prosseguir a
`bmad-architecture`, mas 2 merecem correção antes de gerar épicos/stories
(ver G1, G2).

## Gaps encontrados

### G1 — UJ-2 sem Key Flow dedicado [HIGH]

- **PRD:** §2.3, UJ-2 ("Felipe usa a busca 'rápida e suja' para uma visão
  geral do mercado") — contratar Olheiro Generalista Júnior barato, missão
  rápida sem filtro regional restrito, aceitando relatórios rasos. Referida
  como realizada pelas Features 4.1, 4.2 e 4.3 ("Realiza UJ-1, UJ-2").
- **UX:** `EXPERIENCE.md` §Key Flows — os 4 fluxos nomeados cobrem
  explicitamente UJ-1 (Fluxos 1, 2, 3) e UJ-3 (Fluxo 3); UJ-2 nunca é citada
  como realizada por nenhum fluxo (Fluxo 4/Sonar é explicitamente marcado
  "sem UJ dedicada no PRD", mas isso não supre UJ-2).
- **Impacto:** o caminho "olheiro barato + busca ampla e rasa para visão de
  mercado" — que difere de UJ-1 no objetivo (exploração vs. precisão) e no
  perfil de Olheiro/Missão usado — não tem tela/estado validado
  explicitamente. Fica implícito que o Formulário Nova Missão suporta esse
  caso (nenhum campo o impede), mas nenhuma spine de fluxo comprova isso.
- **Sugestão:** adicionar um Fluxo 5 (ou nota curta dentro de um fluxo
  existente) mostrando Felipe contratando Generalista Júnior e criando uma
  Missão "Rápida" sem filtro geográfico restrito, terminando num Relatório
  raso — reaproveitando os componentes já existentes.

### G2 — Jogador de Referência como filtro de Missão (FR-7) não aparece no UX [HIGH]

- **PRD:** §4.3, FR-7 ("Filtrar por Jogador de Referência") — o usuário
  seleciona um jogador do elenco como critério de busca **na criação da
  Missão**, para encontrar jogadores de perfil semelhante. É um dos filtros
  combináveis citados em FR-4.
- **UX:** `EXPERIENCE.md` menciona "Jogador de Referência" apenas uma vez
  como ação pós-Relatório: botão "Comparar com jogador do elenco" no
  componente Radar de Atributos (linha 83, Detalhe de Jogador) — que
  corresponde a FR-10, não a FR-7. Nem o Formulário Nova Missão (linha 80)
  nem o Fluxo 2 (criação de Missão) citam a seleção de um Jogador de
  Referência como filtro de entrada da busca.
- **Impacto:** FR-7 é um dos filtros centrais do MVP (§6.1 lista
  explicitamente "Jogador de Referência" como filtro em escopo) e não tem
  nenhuma superfície/estado no UX além do uso homônimo, porém distinto, em
  FR-10.
- **Sugestão:** adicionar ao Formulário Nova Missão (Component Patterns e
  Fluxo 2 ou um fluxo novo) um passo de "selecionar Jogador de Referência do
  elenco" como filtro, reaproveitando o "seletor simples do elenco atual"
  já descrito para FR-10, deixando claro que são dois usos do mesmo
  conceito em momentos diferentes (filtro de busca vs. comparação visual).

### G3 — Arquivar/descartar Relatório (FR-8) não modelado [MEDIUM]

- **PRD:** §4.3, FR-8, consequência: "Uma Missão concluída permanece
  visível/acessível até o usuário explicitamente arquivar ou descartar o
  Relatório."
- **UX:** `EXPERIENCE.md` State Patterns (linha 96) só cobre "Missão
  concluída, Relatório não visto" → indicador de "novo" até a primeira
  abertura. Não há estado, ação ou componente para arquivar/descartar um
  Relatório já visto. Buscas por "arquivar"/"descartar" no documento não
  retornam nenhuma ocorrência relacionada a Relatórios (a única ocorrência
  de "descartar" é no contexto de troca de save, linha 99, sem relação).
- **Impacto:** sem essa ação, não fica claro no UX o que limita o
  crescimento da lista de Relatórios/Missões na aba Relatórios/Missões ao
  longo de uma carreira longa.
- **Sugestão:** adicionar uma linha em State Patterns ou Component Patterns
  descrevendo a ação de arquivar/descartar (ex: botão ou swipe-equivalente
  via gamepad/mouse) e o estado resultante (relatório oculto da lista
  principal, mas talvez acessível num filtro "arquivados").

### G4 — Indicador de "precisão estimada" antes de confirmar a Missão (FR-4) ausente [MEDIUM]

- **PRD:** §4.3, FR-4, consequência: "Quanto mais amplo o recorte geográfico
  ..., menor a precisão/Qualidade aplicável ao Relatório resultante —
  refletido visualmente antes de confirmar a Missão (ex: um indicador de
  'precisão estimada')."
- **UX:** `EXPERIENCE.md`, Formulário Nova Missão (linha 80) e Fluxo 2 só
  mencionam "custo/tempo estimado recalculado ao vivo" — nenhuma menção a
  um indicador de precisão/Qualidade estimada reagindo à amplitude
  geográfica antes da confirmação.
- **Impacto:** um dos poucos elementos de feedback antecipado explicitamente
  pedido pelo PRD (para evitar que o usuário só descubra a Qualidade baixa
  depois de gastar orçamento) não tem componente ou estado equivalente no
  UX.
- **Sugestão:** estender a linha do Formulário Nova Missão em Component
  Patterns para incluir um terceiro valor recalculado ao vivo (custo / tempo
  / Qualidade estimada), com o mesmo tratamento visual do Badge de
  Qualidade já definido para Relatórios.

### G5 — Campos do Relatório por jogador (FR-9) não enumerados explicitamente [LOW/MEDIUM]

- **PRD:** §4.4, FR-9 — para cada jogador do Relatório: nome, idade,
  posição nativa (+ Fit Posicional se aplicável), e atributos.
- **UX:** `DESIGN.md` Components → "Card de jogador" cita apenas miniface,
  nome (`heading`) e "atributos-chave" (`body`/`mono`); "Linha de tabela"
  cita só colunas de atributo numérico em `mono`. Nenhum dos dois menciona
  idade, posição nativa ou o indicador de força do Fit Posicional
  (obrigatório por FR-6 quando aplicável). `EXPERIENCE.md` também não
  enumera esses campos em nenhum Component Pattern.
- **Impacto:** menor que G1–G4 porque "atributos-chave" pode
  implicitamente cobrir posição/idade, mas a omissão explícita do
  indicador de Fit Posicional no card/linha do Relatório é uma lacuna
  concreta — FR-6 exige que ele apareça "explicitamente" no Relatório.
- **Sugestão:** adicionar ao Card de jogador / Linha de tabela (DESIGN.md)
  e/ou à descrição do Fluxo 3 (EXPERIENCE.md) os campos idade, posição
  nativa, e badge/indicador de Fit Posicional quando aplicável.

### G6 — Filtros por Overall/Potencial e por atributo dominante não citados nominalmente [LOW]

- **PRD:** §4.3, FR-4 — lista nominalmente 5 categorias de filtro:
  geográfico, Overall/Potencial, atributo dominante, Fit Posicional,
  Jogador de Referência.
- **UX:** `EXPERIENCE.md` só exemplifica nominalmente 2 desses 5 (Filtro
  geográfico via Seletor geográfico, Fit Posicional via Fluxo 2); Overall/
  Potencial e atributo dominante aparecem apenas embutidos na frase genérica
  "Filtros (todos combináveis)" no Formulário Nova Missão, sem componente
  ou exemplo de fluxo dedicado.
- **Impacto:** baixo — a spine claramente pretende ser genérica ("todos
  combináveis"), mas a assimetria (2 filtros exemplificados em detalhe, 3
  omitidos por completo, incluindo o já coberto em G2) sugere que a
  cobertura desses filtros não foi verificada com o mesmo rigor.
- **Sugestão:** opcional — mencionar rapidamente Overall/Potencial e
  atributo dominante como inputs de campo simples (sliders/dropdowns) no
  Formulário Nova Missão, para fechar a lista de 5 filtros do FR-4.

### G7 — Nome de token de design diverge do termo canônico do Glossário [LOW]

- **PRD:** §3, Glossário — Tier `Experiente` é o termo vinculante ("o
  vocabulário do Glossário é vinculante", §0).
- **UX:** `DESIGN.md` nomeia o token/componente como `tier-veteran` /
  `tier-badge-veteran` (inglês "veteran") em vez de algo como
  `tier-experiente`. O texto exibido ao usuário está correto ("EXP", por
  extenso "Experiente" conforme Components), então não há impacto visível
  ao usuário final — mas o nome interno do token diverge do termo canônico,
  o que pode confundir uma futura implementação/arquitetura que procure o
  termo do Glossário literalmente nos nomes de variáveis/tokens.
- **Sugestão:** renomear os tokens `tier-veteran`/`tier-badge-veteran` para
  `tier-experiente`/`tier-badge-experiente` por consistência terminológica,
  ou documentar explicitamente o mapeamento inglês↔português no próprio
  `DESIGN.md`.

## Verificações sem gap (positivas)

- **FR-1, FR-2, FR-3, FR-5, FR-6, FR-10, FR-11** têm superfície/fluxo/estado
  correspondente claro no `EXPERIENCE.md` (IA, Component Patterns, State
  Patterns e/ou Key Flows).
- **UJ-1** e **UJ-3** são cobertas explicitamente por Key Flows nomeados
  (Fluxos 1–3).
- Termos do Glossário (Olheiro, Especialização, Tier, Missão, Modo de
  Busca, Filtro, Fit Posicional, Relatório, Qualidade, Sonar de Cobertura,
  Radar de Atributos, Orçamento de Scouting) são usados de forma
  consistente no `EXPERIENCE.md` — inclusive "Orçamento de Scouting" é
  reutilizado ali com mais disciplina do que no próprio PRD (que mistura
  "orçamento do clube" e o termo do Glossário; achado já registrado em
  `review-rubric.md` do PRD).
- A Questão em Aberto #5 do PRD (troca de save com Missões pendentes) é
  tratada explicitamente em `EXPERIENCE.md` (State Patterns, linha 99) com
  `[NOTE FOR PM]` + `[ASSUMPTION]` rotulados corretamente, sem fingir uma
  decisão que o PRD não tomou — tratamento exemplar de uma lacuna
  conhecida.
- O tom/voz da conversa PM↔usuário (feature hobby, sem "cheat sem custo",
  sem gamificação de urgência, registro "central de operações séria" que
  não compete visualmente com o jogo) foi capturado tanto em
  `DESIGN.md.Brand & Style` quanto em `EXPERIENCE.md.Voice and Tone` — não
  identificamos intenção qualitativa relevante perdida entre PRD/memlog e
  UX.

## Nota final

Nenhum gap crítico/bloqueante encontrado — mas G1 e G2 (HIGH) devem ser
corrigidos no `EXPERIENCE.md` antes de `bmad-create-epics-and-stories`,
pois cobrem uma Jornada-Chave inteira (UJ-2) e um Requisito Funcional
inteiro (FR-7) sem qualquer superfície equivalente hoje.
