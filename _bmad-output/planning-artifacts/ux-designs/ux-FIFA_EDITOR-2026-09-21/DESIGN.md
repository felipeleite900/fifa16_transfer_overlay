---
name: Central de Scout
description: Painel de scouting dentro do overlay ImGui do FIFA 16 Companion. Escuro/gamer, roxo de marca contra verde-campo, denso o suficiente para power users, nunca competindo visualmente com o jogo rodando por trás.
status: final
created: 2026-09-21
updated: 2026-09-21
sources:
  - "{planning_artifacts}/prds/prd-FIFA_EDITOR-2026-09-21/prd.md"
colors:
  bg-base: '#0b0e0c'
  bg-panel: 'rgba(16,20,18,0.93)'
  bg-panel-raised: 'rgba(24,29,26,0.96)'
  border-hairline: 'rgba(180,92,255,0.28)'
  border-hairline-subtle: 'rgba(255,255,255,0.08)'
  text-primary: '#e9f2ec'
  text-secondary: '#869488'
  text-disabled: '#4d564f'
  accent-primary: '#b45cff'
  accent-primary-dim: 'rgba(180,92,255,0.13)'
  field-green: '#3ecf6e'
  tier-elite: '#f5a623'
  tier-experiente: '#b45cff'
  tier-junior: '#5c6b5f'
  success: '#3ecf6e'
  warning: '#f5a623'
  danger: '#e5484d'
  quality-low: '#5c6b5f'
  quality-medium: '#b45cff'
  quality-high: '#f5a623'
typography:
  display:
    fontFamily: 'Oswald'
    fontWeight: 600
    note: 'Condensada, tipo placar/HUD esportivo. Reservada para título do painel e valores numéricos de destaque (overall, potencial).'
  heading:
    fontFamily: 'Oswald'
    fontWeight: 500
    note: 'Títulos de aba, nomes de Olheiro/jogador em cards.'
  body:
    fontFamily: 'Inter'
    fontWeight: 400
    note: 'Corpo de texto, valores de tabela, labels de filtro.'
  meta:
    fontFamily: 'Inter'
    fontWeight: 400
    note: 'Texto secundário pequeno — timestamps, contadores, hints.'
  mono:
    fontFamily: 'Consolas'
    fontWeight: 400
    note: 'Valores numéricos tabulares (colunas de atributo) para alinhamento vertical perfeito dígito-a-dígito.'
rounded:
  sm: 4px
  md: 8px
  lg: 12px
  DEFAULT: 6px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
  '6': 32px
components:
  panel-window:
    background: '{colors.bg-panel}'
    border: '1px solid {colors.border-hairline}'
    rounded: '{rounded.lg}'
  tab-bar:
    background: 'transparent'
    activeBackground: '{colors.accent-primary}'
    activeText: '{colors.bg-base}'
    inactiveText: '{colors.text-secondary}'
    rounded: '{rounded.md}'
  tier-badge-junior:
    background: 'transparent'
    border: '1px solid {colors.tier-junior}'
    text: '{colors.tier-junior}'
    rounded: '{rounded.sm}'
  tier-badge-experiente:
    background: '{colors.accent-primary-dim}'
    border: '1px solid {colors.tier-experiente}'
    text: '{colors.tier-experiente}'
    rounded: '{rounded.sm}'
  tier-badge-elite:
    background: 'transparent'
    border: '1px solid {colors.tier-elite}'
    text: '{colors.tier-elite}'
    rounded: '{rounded.sm}'
  button-primary:
    background: '{colors.field-green}'
    text: '{colors.bg-base}'
    rounded: '{rounded.DEFAULT}'
  button-secondary:
    background: 'transparent'
    border: '1px solid {colors.border-hairline}'
    text: '{colors.text-primary}'
    rounded: '{rounded.DEFAULT}'
  progress-bar-track:
    background: '{colors.bg-panel-raised}'
    rounded: '{rounded.sm}'
  progress-bar-fill:
    background: '{colors.accent-primary}'
    rounded: '{rounded.sm}'
---

## Brand & Style

A Central de Scout precisa fazer duas coisas que puxam em direções opostas ao
mesmo tempo: (1) parecer uma ferramenta séria de recrutamento — densa,
confiável, quase profissional — e (2) nunca competir visualmente com o jogo
colorido e vibrante rodando por trás dela em tela cheia. A resposta é um
registro "console de operações escuro": fundo quase preto com um leve tint
verde-gramado (não preto puro, não azul-frio genérico de app corporativo),
painéis semi-transparentes que deixam o jogo "respirar" ao redor das bordas,
e um único acento cromático forte — roxo — reservado para marca e ação
primária, nunca disperso pela tela.

**Nota de calibração (revisão pós-mockup):** a primeira rodada de mockups
pecou para o lado "neon" — glow/gradiente ambiente simulando aura ao redor
do painel, e badges de Tier/Qualidade em preenchimento sólido muito
saturado. Isso não é o registro pretendido. O roxo e o verde-campo
permanecem os mesmos tons (`accent-primary` `#b45cff`, `field-green`
`#3ecf6e`) — o ajuste é de **aplicação**, não de paleta: sem glow/gradiente
de fundo simulando irradiação luminosa (o fundo é liso, só o tint sutil de
`bg-base`), e badges usam contorno + preenchimento tênue (`accent-primary-dim`
ou transparente) em vez de fundo sólido saturado. O efeito "console sério",
não "painel cyberpunk".

O verde-campo entra como segunda cor com propósito duplo: remete à
identidade de futebol sem imitar literalmente os cards/menus do FIFA (o que
pareceria clone barato), e serve como cor semântica de "sucesso/disponível"
— um verde que já é familiar ao contexto sem precisar ser explicado. O
dourado do Tier Elite e o cinza-esverdeado do Tier Júnior fecham uma escala
de três degraus lida de forma intuitiva por qualquer jogador de RPG/gestão:
cinza é básico, roxo é intermediário, dourado é o topo.

A tipografia reforça o registro de "central de operações": uma condensada
tipo HUD esportivo para números e títulos (onde a leitura rápida de um
placar importa), e uma sans-serif limpa para tudo que exige leitura
prolongada (labels, descrições, texto de filtro).

## Colors

- **Fundo base (`#0b0e0c`)** é quase preto com leve tint verde — nunca preto
  puro (frio demais) nem cinza neutro (sem personalidade). É a cor por trás
  de tudo, mas como o overlay é semi-transparente sobre o jogo, na prática
  aparece pouco — o painel (`bg-panel`) domina visualmente.
- **Painel (`rgba(16,20,18,0.93)`)** é a superfície de conteúdo — abas,
  listas, formulários vivem aqui. A transparência de 93% garante legibilidade
  total do texto sem apagar completamente o jogo nas bordas do overlay.
  `bg-panel-raised` (96% opaco) marca elementos "acima" do painel base —
  modais de confirmação, trilhos de barra de progresso.
- **Roxo (`accent-primary`, `#b45cff`)** é a cor de marca — usada em: aba
  ativa, badge de Tier Experiente, barra de progresso de Missão, e qualquer
  elemento que precise dizer "isto é Central de Scout". Nunca usado para
  erro ou perigo.
- **Verde-Campo (`field-green`, `#3ecf6e`)** é a cor de ação positiva/sucesso
  — botão primário (Contratar, Confirmar Missão), status "Disponível" de
  Olheiro, indicador de Missão concluída.
- **Dourado (`tier-elite`, `#f5a623`)** é reservado exclusivamente para o
  Tier Elite e para o nível mais alto de Qualidade de relatório — nunca usado
  decorativamente, sempre carrega o significado "o mais alto nível".
- **Cinza-esverdeado (`tier-junior`, `#5c6b5f`)** marca o nível básico —
  Tier Júnior, Qualidade baixa. É deliberadamente discreto, para não competir
  com roxo/dourado.
- **Vermelho (`danger`, `#e5484d`)** é usado com extrema parcimônia — apenas
  para bloqueios reais (orçamento insuficiente, erro de leitura do save).
  Nunca usado como "quarto degrau" de Tier ou Qualidade.

Evitar: gradientes e glow/aura simulando irradiação luminosa ao redor de
painéis ou textos (o painel é uma superfície de dados, não uma peça de
marketing ou HUD cyberpunk), preenchimento sólido saturado em badges (usar
contorno + preenchimento tênue, ver Components), qualquer cor
pastel/dessaturada fora da escala definida, e opacidade abaixo de 90% em
painéis com texto (compromete legibilidade sobre o jogo colorido rodando
atrás).

## Typography

Dois papéis fazem o trabalho pesado: `display`/`heading` (Oswald condensada)
para tudo que precisa ser lido rapidamente à distância — título do painel,
nomes de Olheiro, valores de Overall/Potencial em destaque — e `body`/`meta`
(Inter) para texto de leitura contínua — descrições, labels de filtro, texto
de estado.

`mono` (Consolas) é um papel adicional específico deste produto: qualquer
coluna de atributos numéricos na visão Tabular (FR-9) usa fonte monoespaçada,
para que os dígitos alinhem verticalmente entre linhas — essencial numa
tabela densa onde o usuário compara Overall/Potencial de vários jogadores de
uma vez.

Sem itálico (não combina com o registro "HUD"). Uso de maiúsculas reservado
a badges de Tier/Qualidade (curtos, 3-5 caracteres) — nunca em frases
inteiras.

## Layout & Spacing

Escala: 4 / 8 / 12 / 16 / 24 / 32px — mapeada a `{spacing.1}` até
`{spacing.6}`. Painéis internos (cards, linhas de tabela) usam o espaçamento
mais apertado (`{spacing.2}`–`{spacing.3}`); separação entre blocos
maiores (ex: entre a barra de abas e o conteúdo, entre seções de um
formulário de Missão) usa `{spacing.5}`–`{spacing.6}`.

O painel inteiro tem uma largura/altura máxima pensada para não cobrir a
tela toda — sempre deixa uma margem visível do jogo ao redor (o usuário
ainda precisa sentir que está "sobre" o FIFA, não "dentro" de um app
separado). `[ASSUMPTION]` Dimensão de referência: ~70% da largura e ~75% da
altura da resolução de jogo, centralizado.

## Elevation & Depth

Sem sombras — ImGui não renderiza esse tipo de profundidade nativamente de
forma barata, e uma central de scouting não precisa da metáfora. Hierarquia
vem de opacidade (`bg-panel` vs. `bg-panel-raised`) e de borda: elementos
"acima" do painel base (tooltips, confirmação de contratação, modal de
detalhe de jogador) usam uma borda mais visível (`border-hairline` em vez de
`border-hairline-subtle`) para se destacar sem precisar de sombra.

## Shapes

`rounded/sm` (4px) para badges de Tier/Qualidade e barras de progresso —
pequenos elementos que não devem chamar atenção pela forma. `rounded/md`
(8px) para botões e abas. `rounded/lg` (12px) para o contêiner do painel
principal e para cards de jogador na visão espaçosa. Nada totalmente
arredondado (sem pills) — o registro é "console", não "app consumer".

## Components

→ 7 mocks em `mockups/` ilustram estes componentes aplicados
(`olheiros.html`, `nova-missao.html`, `selecao-geografica.html`,
`missoes.html`, `relatorio.html`, `ficha-jogador.html`, `sonar.html`).
Spine vence em caso de conflito com qualquer mock.

- **Painel principal (`panel-window`)** — Contêiner raiz de toda a Central
  de Scout. Borda roxa sutil (`border-hairline`), cantos `rounded.lg`.
- **Barra de abas (`tab-bar`)** — 4 abas fixas (Olheiros / Missões /
  Relatórios / Sonar). Aba ativa em fundo roxo sólido com texto escuro;
  inativas em texto secundário sem fundo.
- **Badge de Tier** (`tier-badge-junior` / `-experiente` / `-elite`) — Pequeno
  rótulo em **contorno** (cinza / roxo / dourado) com preenchimento
  transparente ou tênue (`accent-primary-dim` no caso de Experiente) e texto
  na mesma cor do contorno — nunca fundo sólido saturado, nunca só a cor sem
  o texto por extenso (`JR` / `EXP` / `ELITE`). Mesma estrutura visual
  reaproveitada para o indicador de Qualidade de relatório (`quality-low` /
  `-medium` / `-high`), com os textos "Baixa" / "Média" / "Alta" em vez do
  nome do Tier.
- **Botão primário (`button-primary`)** — Verde-campo sólido, texto escuro,
  usado para a ação principal de cada tela (Contratar, Confirmar Missão).
- **Botão secundário (`button-secondary`)** — Transparente com borda roxa
  sutil, usado para ações não-destrutivas alternativas (Cancelar, Voltar).
- **Barra de progresso de Missão** (`progress-bar-track` +
  `progress-bar-fill`) — Trilho em `bg-panel-raised`, preenchimento em roxo
  sólido. Sempre acompanhada de texto de estimativa (`meta`) — nunca a barra
  sozinha.
- **Card de jogador (visão espaçosa)** — `rounded.lg`, `bg-panel-raised`,
  com a **miniface real** do jogador (lida de
  `data/ui/imgAssets/heads/p<PLAYERID>.dds`, já confirmado viável no
  `PROJECT_MEMORY.md`) sempre no topo — nunca um placeholder genérico
  quando o arquivo existe para aquele `playerid`; cai num ícone silhueta
  neutro apenas se o arquivo não existir. Nome em `heading`, e logo abaixo:
  idade, posição nativa, e atributos-chave em `body`/`mono`. Quando o Fit
  Posicional se aplica (FR-6), um badge adicional mostra a posição-alvo e a
  força do encaixe, na mesma linha da posição nativa.
- **Formulário em lista vertical** — Usado no Formulário Nova Missão.
  Cada linha de configuração ocupa a largura toda do painel, com o rótulo
  do campo à esquerda e o valor atual/resumo à direita, em `bg-panel-raised`
  com divisor hairline entre linhas — o mesmo padrão visual de uma tela de
  configurações de console. Linha em foco (D-pad ou hover) ganha
  `border-hairline` completo ao redor. Um rodapé fixo (fora da lista
  rolável) mostra o resumo de custo/tempo/Qualidade estimada, sempre
  visível.
- **Painel em tela cheia (campo dedicado)** — Usado quando uma linha do
  Formulário abre um subcampo complexo (Seleção Geográfica, Fit Posicional,
  Jogador de Referência, Atributo dominante). Ocupa a área de conteúdo
  inteira do `panel-window` (a barra de abas e o cabeçalho do painel
  permanecem visíveis para orientação). Cantos `rounded.md`, mesma paleta
  do painel principal — não é um "novo estilo", é uma extensão em foco
  total do mesmo formulário.
- **Linha de tabela (visão densa)** — Sem card, apenas divisor hairline
  entre linhas; colunas fixas na ordem nome → idade → posição nativa →
  (Fit Posicional, se aplicável) → colunas de atributo numérico em `mono`
  para alinhamento.
- **Radar de Atributos** — Desenhado via ImGui draw list customizado
  (`ImDrawList`); contorno em roxo sólido para o jogador principal,
  contorno em verde-campo tracejado quando há sobreposição de Jogador de
  Referência. Eixos sem valor revelado (Qualidade baixa) aparecem
  pontilhados/vazios, nunca com valor inventado.
- **Sonar de Cobertura (mapa)** — Mapa-mundi estilizado com países
  representativos desenhados como formas individuais (não um contorno
  geográfico realista completo, mas granularidade por país — conforme PRD
  FR-11 — e não apenas por continente), desenhado via `ImDrawList`. Cada
  país usa a escala de Qualidade/Tier por preenchimento: sem preenchimento =
  nunca escaneado, contorno roxo + preenchimento tênue = Missão ativa,
  contorno verde-campo + preenchimento tênue = Missão concluída (Relatório
  disponível) — mesma lógica de contorno-primeiro usada nos badges, sem
  preenchimento sólido saturado.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Roxo reservado para marca/ação primária de identidade (abas, Tier Experiente, progresso) | Espalhar roxo em qualquer elemento decorativo sem função semântica |
| Badges e regiões do mapa em contorno + preenchimento tênue | Fundo sólido saturado em badges, ou glow/aura simulando irradiação luminosa |
| Todo indicador crítico (Tier, status, Qualidade) com cor + texto/ícone junto | Badges que dependem só da cor para serem entendidos |
| Opacidade de painel ≥ 90% | Painéis translúcidos a ponto de comprometer leitura sobre o jogo |
| Fonte monoespaçada em colunas de atributo numérico | Números de tabela em fonte proporcional (desalinha visualmente) |
| Dourado exclusivo para Tier Elite / Qualidade Alta | Usar dourado decorativamente em outros contextos |
| Manter margem visível do jogo ao redor do painel | Painel cobrindo 100% da tela |
