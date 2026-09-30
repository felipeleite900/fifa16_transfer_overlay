---
name: Central de Scout
status: final
created: 2026-09-21
updated: 2026-09-21
sources:
  - "{planning_artifacts}/prds/prd-FIFA_EDITOR-2026-09-21/prd.md"
---

# Central de Scout — Experience Spine

> Painel único dentro do overlay ImGui (`fifa_overlay`, Rust) do FIFA 16
> Companion. Sem UI system tradicional (não é web/mobile) — `DESIGN.md` é a
> referência de identidade visual; esta spine descreve comportamento,
> estados e fluxos. Input híbrido (mouse+teclado e gamepad). Texto em
> português.

## Foundation

Superfície única: um painel overlay renderizado por cima do FIFA 16 em
fullscreen exclusivo, via hook de `Present()` já validado
(`PROJECT_MEMORY.md`, sessão 5). Não há múltiplas janelas nem navegação de
sistema operacional — tudo acontece dentro do mesmo painel ImGui.

Nenhum UI system é herdado (ImGui puro com tema customizado, ver
`DESIGN.md`). Dois modos de input são suportados com paridade: mouse +
teclado (cursor assumido pelo overlay enquanto o painel está aberto, como
outros overlays de jogo) e gamepad (navegação inteira por D-pad/analógico +
botões, sem exigir mouse). Foco visual claro em ambos os modos — ver
Accessibility Floor.

O painel só está disponível quando o FIFA 16 tem uma carreira carregada
(dependência de leitura do save ativo). Fora disso, o painel abre em estado
vazio explicativo (ver State Patterns).

## Information Architecture

| Superfície | Alcançada a partir de | Propósito |
|---|---|---|
| Painel Scout (raiz) | Atalho/combo dedicado (qualquer momento em Modo Carreira) | Contêiner das 4 abas |
| Aba Olheiros | Barra de abas | Listar Olheiros contratados + contratar novos → `mockups/olheiros.html` |
| Aba Missões | Barra de abas | Criar Missão nova + acompanhar Missões ativas → `mockups/missoes.html` |
| Aba Relatórios | Barra de abas | Ver Relatórios de Missões concluídas → `mockups/relatorio.html` |
| Aba Sonar | Barra de abas | Mapa de cobertura geográfica de Missões, por país → `mockups/sonar.html` |
| Ficha de Jogador | Tap/clique num jogador de um Relatório | Bio + atributos completos + Radar, com comparação a Jogador de Referência → `mockups/ficha-jogador.html` |
| Formulário Nova Missão | Botão "Nova Missão" na aba Missões | Lista vertical de linhas de configuração (Olheiro, Filtros, Modo de Busca) → `mockups/nova-missao.html` |
| Painel de Seleção Geográfica (tela cheia) | Ativar a linha "Filtro geográfico" no Formulário Nova Missão | Selecionar países no mapa Sonar em modo seleção, com espaço total de tela → `mockups/selecao-geografica.html` |
| Confirmação de Contratação | Botão "Contratar" num Olheiro disponível | Confirmar custo antes de debitar o Orçamento de Scouting |

Barra de abas fixa e sempre visível no topo do painel (Olheiros / Missões /
Relatórios / Sonar). Sem menu hambúrguer. Navegação aninhada de no máximo
dois níveis para o único caso que exige (Formulário Nova Missão → Painel de
Seleção Geográfica em tela cheia, ver Component Patterns); todas as demais
superfícies satélite (Ficha de Jogador, Confirmação de Contratação) abrem
*sobre* a aba atual, um nível só.

→ Referência de composição: 7 mocks em `mockups/` (ver tabela acima e
Component Patterns para links por seção). Spine vence em caso de conflito
com qualquer mock.

## Voice and Tone

Microcopy em português, direta e sem gamificação de urgência. Voz e postura
de marca vivem em `DESIGN.md.Brand & Style`.

| Faça | Evite |
|---|---|
| "Orçamento insuficiente: faltam R$ 2.1M." | "Ops! Você não tem dinheiro suficiente 😅" |
| "Relatório pronto." | "🎉 Novo relatório disponível!!!" |
| "Nenhum Olheiro contratado ainda." | "Comece agora sua jornada de scouting!" |
| Números e prazos exatos sempre que a Qualidade permitir. | Linguagem vaga quando um valor exato está disponível. |
| Frases curtas e completas. | Pontos de exclamação, emojis, tom de gamificação/urgência artificial. |

## Component Patterns

Comportamental. Especificação visual vive em `DESIGN.md.Components`.

| Componente | Uso | Regras comportamentais |
|---|---|---|
| Barra de abas | Raiz do painel | 4 abas fixas. Troca de aba preserva o estado de scroll/seleção da aba anterior (não reseta ao voltar). |
| Card de Olheiro | Aba Olheiros | Mostra Especialização, Tier (badge), status (Disponível / Em Missão), botão Contratar ou indicador de ocupado. → `mockups/olheiros.html` |
| Linha/Card de jogador | Relatório, ambas as densidades | Tap/clique abre Ficha de Jogador. Densidade (Tabular vs. Cards) é uma preferência persistente do usuário, alternável por um toggle sempre visível no topo da aba Relatórios. Na densidade Cards, cada jogador exibe sua miniface real (lida de `data/ui/imgAssets/heads/p<PLAYERID>.dds`) — nunca um placeholder genérico quando o arquivo existe; se o arquivo não existir para aquele `playerid`, cai num ícone silhueta neutro. → `mockups/relatorio.html` |
| Toggle de densidade | Aba Relatórios | Dois estados: Tabular / Cards. Persiste entre sessões (não reseta a cada abertura do painel). → `mockups/relatorio.html` |
| Formulário Nova Missão | Aba Missões → botão dedicado | **Lista vertical de linhas de configuração**, estilo menu de configurações de console (Xbox/PlayStation) — uma linha por campo, navegação por D-pad/analógico cima-baixo sem exigir alcance lateral. Os 5 Filtros do PRD (FR-4) e o Modo de Busca (FR-5) são linhas dessa lista: Olheiro, Filtro geográfico, Overall/Potencial, Atributo dominante, Fit Posicional, Jogador de Referência, Modo de Busca. Ativar uma linha (botão A do gamepad / clique) abre um **painel dedicado em tela cheia** para aquele campo específico quando o campo tem complexidade própria (Filtro geográfico → Painel de Seleção Geográfica; Jogador de Referência/Fit Posicional/Atributo dominante → lista de opções em tela cheia); campos simples de faixa numérica (Overall/Potencial) ajustam-se inline na própria linha sem abrir painel. Um resumo fixo no rodapé (custo / tempo / Qualidade estimada, recalculado ao vivo) permanece visível mesmo dentro dos painéis de campo, para nunca exigir "voltar para conferir". → `mockups/nova-missao.html` |
| Painel de Seleção Geográfica | Ativado pela linha "Filtro geográfico" do Formulário Nova Missão | Reaproveita o Mapa Sonar (mesmo desenho de países individuais) em modo seleção, mas em **tela cheia** — não encaixotado dentro do formulário. Navegação por gamepad: D-pad move um cursor entre países vizinhos (ordem de adjacência geográfica simplificada); botão A alterna inclusão/exclusão do país no filtro; botão B/RB confirma e retorna ao Formulário. Multi-seleção via ativação cumulativa (sem precisar segurar modificador), compatível com mouse (clique) e gamepad igualmente. → `mockups/selecao-geografica.html` |
| Seletor de elenco (Jogador de Referência) | Dentro do Formulário Nova Missão, como linha de configuração (Filtro por Jogador de Referência, FR-7) **e** dentro da Ficha de Jogador (comparação, FR-10) | Mesmo componente — lista em tela cheia do elenco atual — reaproveitado em dois momentos distintos: como **filtro de busca** ao criar a Missão (orienta a similaridade da pesquisa) e como **comparação visual** após o Relatório pronto (sobrepor radares). O rótulo do componente deixa claro qual dos dois papéis está ativo em cada contexto. |
| Barra de progresso de Missão | Aba Missões, Missão ativa | Preenchimento proporcional ao avanço de `GJUr.currdate` desde a criação até o prazo estimado. Texto de estimativa sempre visível junto (nunca só a barra). → `mockups/missoes.html` |
| Ficha de Jogador | Aba Relatórios → tap/clique num jogador | Tela única e completa: cabeçalho biográfico (nome, idade, posição nativa + Fit Posicional se aplicável, pé preferido, nacionalidade), lista completa de atributos numéricos revelados, e o Radar de Atributos — tudo visível ao mesmo tempo, sem sub-abas. Botão "Comparar com jogador do elenco" sempre visível e acessível a partir desta mesma tela. → `mockups/ficha-jogador.html` |
| Radar de Atributos | Dentro da Ficha de Jogador (um dos três blocos da tela, não uma tela própria) | Eixos = atributos revelados pela Qualidade do Relatório. Sobreposição de Jogador de Referência é opcional, ativada pelo botão "Comparar com jogador do elenco" da Ficha, que abre o Seletor de elenco. → `mockups/ficha-jogador.html` |
| Mapa Sonar (modo visualização) | Aba Sonar | Somente leitura, granularidade **por país** (não por continente) — cada país é uma forma individual no mapa estilizado. Clique/toque num país abre um resumo textual (quantas Missões ativas/concluídas ali), sem navegar para outra aba. → `mockups/sonar.html` |
| Badge de Tier / Qualidade | Onipresente (Olheiros, Missões, Relatórios) | Sempre cor + texto (ver Accessibility Floor). Visual em contorno + preenchimento tênue (ver `DESIGN.md.Components`), nunca fundo sólido saturado. Nunca só cor. |

## State Patterns

| Estado | Superfície | Tratamento |
|---|---|---|
| Sem carreira carregada | Painel Scout (qualquer aba) | Estado vazio: "Nenhuma carreira carregada. Abra uma carreira no FIFA 16 para usar a Central de Scout." Sem tentar renderizar dados. |
| Nenhum Olheiro contratado | Aba Olheiros | "Nenhum Olheiro contratado ainda." + lista de Olheiros disponíveis para contratar já visível abaixo (não é um beco sem saída). |
| Orçamento insuficiente | Confirmação de Contratação / Confirmação de Missão | Botão de confirmar desabilitado + texto exato do valor faltante (ver Voice and Tone). Nunca falha silenciosamente após o clique. |
| Olheiro ocupado em Missão | Aba Olheiros, ao tentar iniciar nova Missão | Olheiro aparece com badge "Em Missão" e não é selecionável no Formulário Nova Missão. |
| Missão em andamento | Aba Missões | Barra de progresso + "pronto em ~N dias de carreira" (ver `DESIGN.md.Components`). Recalculado a cada abertura do painel, não em tempo real. |
| Missão concluída, Relatório não visto | Aba Missões e Aba Relatórios | Indicador visual de "novo" no card da Missão/Relatório até o usuário abrir o Relatório pela primeira vez. |
| Relatório arquivado | Aba Relatórios | Ação "Arquivar" disponível em qualquer Relatório já visto (botão na Ficha de Jogador ou na lista). Relatório arquivado some da lista principal mas fica acessível num filtro "Arquivados" — nunca apagado de vez, já que o custo de gerá-lo (Orçamento de Scouting) foi real. |
| Relatório com Qualidade baixa | Ficha de Jogador, bloco Radar | Eixos não revelados aparecem vazios/pontilhados — nunca com valor inventado ou zerado (zero seria enganoso, pareceria um atributo real). |
| Erro de leitura do save | Painel Scout (qualquer aba) | Mensagem clara "Não foi possível ler o save ativo." com opção de tentar novamente — nunca trava o painel sem explicação. |
| Troca de save ativo com Missões pendentes | Painel Scout | `[NOTE FOR PM]` Comportamento ainda não definido no PRD (Questão em Aberto #5) — nesta spine, assumir `[ASSUMPTION]` que o painel detecta a troca e avisa "Este save tem Missões de um save diferente — [ver mesmo assim] [descartar]", até a decisão de arquitetura ser tomada. |

## Interaction Primitives

- **Mouse + teclado:** clique para selecionar/confirmar; hover para
  destacar linha/card antes do clique; scroll do mouse rola listas longas
  (Olheiros, Relatórios).
- **Gamepad:** D-pad/analógico esquerdo move o foco entre elementos
  navegáveis (abas → cards → botões, ordem de leitura); botão de confirmação
  do controle ativa o elemento em foco; botão de cancelar fecha
  modais/volta uma tela; gatilhos (LB/RB ou L1/R1) trocam de aba
  diretamente sem precisar navegar até a barra de abas.
- **Ambos os modos:** o elemento em foco/hover tem destaque visual idêntico
  (borda roxa sólida), para que trocar de mouse para controle no meio de
  uma sessão nunca deixe o usuário sem noção de onde está.
- **Banido:** gestos de swipe (sem sentido em overlay de PC), animações de
  entrada longas ao trocar de aba (o painel deve responder instantaneamente,
  já que está sobre um jogo rodando a ~60fps), sons/vibração adicionais além
  do que o próprio FIFA já produz.

## Accessibility Floor

Comportamental. Contraste visual vive em `DESIGN.md`.

- Todo indicador crítico (Tier, status de Missão, Qualidade de Relatório)
  carrega cor **e** texto/ícone — nunca só cor (decisão explícita, ver
  memlog). Cobre daltonismo sem exigir modo separado.
- Foco de teclado/gamepad sempre visível e sequencial (ordem de leitura:
  abas → conteúdo principal → ações). Nenhum elemento interativo sem estado
  de foco visível.
- Alvos de clique/toque (mesmo em overlay de mouse) com área mínima
  confortável para clique impreciso — `[ASSUMPTION]` equivalente a 32px
  visuais mínimos por elemento interativo, adaptado do padrão mobile
  (44pt/48dp) para o contexto de mouse de desktop.
- Texto nunca depende só de tamanho pequeno para caber — colunas da visão
  Tabular truncam com reticências e tooltip completo no hover/foco, em vez
  de reduzir fonte agressivamente.

## Key Flows

### Fluxo 1 — Felipe contrata um Olheiro Tático (realiza UJ-1 do PRD)

1. Felipe abre o overlay, depois aciona o atalho da Central de Scout.
2. Painel abre na última aba usada (ou Olheiros, se primeira vez).
3. Na aba Olheiros, vê Olheiros contratados (se houver) e a lista de
   disponíveis para contratar, cada um com Especialização, Tier e custo.
4. Seleciona Tático + Experiente → confirma no diálogo de Confirmação de
   Contratação, que mostra o custo exato e o Orçamento de Scouting
   resultante antes de debitar.
5. Confirma. Orçamento é debitado (`transferbudget`), releitura confirma o
   novo saldo exibido no painel.
6. **Clímax:** o novo Olheiro aparece na lista com status "Disponível",
   pronto para receber uma Missão — a transição de "escolha" para "ativo"
   é instantânea e visível, sem espera adicional.

Falha: se o orçamento for insuficiente, o passo 4 já desabilita o botão de
confirmar e mostra o valor faltante — Felipe nunca chega a tentar confirmar
algo que vai falhar.

### Fluxo 2 — Felipe cria uma Missão com Fit Posicional, navegando de controle (realiza UJ-1 do PRD)

1. Na aba Missões, Felipe navega até "Nova Missão" com o D-pad e confirma.
2. Formulário abre como lista vertical de linhas de configuração. Felipe
   desce até a linha "Olheiro" e seleciona o Tático recém-contratado (únicos
   Olheiros "Disponíveis" aparecem selecionáveis).
3. Desce até a linha "Fit Posicional", ativa e escolhe posição-alvo
   "Volante" na lista em tela cheia que se abre.
4. Desce até a linha "Filtro geográfico", confirma para abrir o Painel de
   Seleção Geográfica em tela cheia; navega entre países vizinhos com o
   D-pad, marcando os da América do Sul e da Europa um a um; confirma para
   voltar ao Formulário.
5. Desce até "Modo de Busca", escolhe "Completa" — o resumo fixo no rodapé
   (custo, tempo e Qualidade estimada, badge "Alta") recalcula ao vivo a
   cada mudança, sempre visível mesmo enquanto Felipe estava dentro dos
   painéis de campo, dando confiança antes de confirmar.
6. Confirma a Missão. Orçamento debitado, Olheiro passa a status
   "Em Missão".
7. **Clímax:** a aba Missões mostra a nova Missão com barra de progresso
   zerada e a estimativa "pronto em ~14 dias de carreira" — Felipe sabe
   exatamente quando voltar a olhar, tendo configurado tudo sem tocar em
   mouse ou teclado uma única vez.

Edge case: se Felipe tentar remover o único Olheiro selecionado sem
escolher outro, o botão de confirmar permanece desabilitado (Missão sempre
exige um Olheiro válido, ver PRD FR-4).

### Fluxo 3 — Felipe recebe e explora um Relatório (realiza UJ-1, UJ-3 do PRD)

1. Dias depois, Felipe reabre o painel — a aba Missões mostra a Missão como
   "Concluída" com indicador de "novo".
2. Ele vai para a aba Relatórios, abre o novo Relatório.
3. Vê a lista de jogadores encontrados na densidade escolhida — se for
   Cards, já reconhece o rosto de um jogador que talvez tenha visto antes na
   base, pela miniface real exibida no card.
4. Toca num jogador → Ficha de Jogador abre com bio completa, todos os
   atributos revelados e o Radar, tudo na mesma tela.
5. Toca "Comparar com jogador do elenco", escolhe seu volante titular.
6. **Clímax:** dois radares sobrepostos (roxo sólido = jogador encontrado,
   verde-campo tracejado = titular atual), lado a lado com o restante da
   ficha (idade, posição, atributos completos) sempre visível — Felipe vê
   de relance, sem trocar de tela, se vale a pena ir negociar esse jogador
   no FIFA.

Estado alternativo: se a Qualidade do Relatório for baixa, o Radar mostra
menos eixos preenchidos — Felipe entende visualmente (eixos pontilhados)
que a informação é parcial, não que o jogador tem atributos zerados.

### Fluxo 4 — Felipe usa a busca rápida e suja para uma visão geral do mercado (realiza UJ-2 do PRD)

1. No início de uma nova carreira, com pouco Orçamento de Scouting, Felipe
   abre a aba Olheiros e contrata um Generalista Júnior (o mais barato
   disponível).
2. Vai para a aba Missões, toca "Nova Missão", seleciona o Generalista
   Júnior recém-contratado.
3. Não restringe o Filtro geográfico (deixa todos os continentes
   marcados) e não ativa Fit Posicional nem Jogador de Referência — só os
   filtros básicos de Overall/Potencial em faixa ampla.
4. Escolhe Modo de Busca "Rápida". O indicador de Qualidade estimada ao
   vivo já mostra "Baixa" (badge cinza) antes mesmo de confirmar — Felipe
   sabe exatamente a troca que está fazendo.
5. Confirma a Missão (custo baixo, tempo curto).
6. **Clímax:** o Relatório chega rápido com uma lista longa de jogadores,
   cada um com poucos atributos revelados e faixas largas (ex:
   "Overall: 65-78") — suficiente para Felipe identificar rapidamente em
   quais regiões investir Olheiros melhores depois, sem esperar muito nem
   gastar muito.

Contraste com Fluxo 2: mesma superfície (Formulário Nova Missão), mas o
indicador de Qualidade estimada e o Modo de Busca guiam o usuário para um
resultado deliberadamente raso — nenhuma tela nova é necessária, só
combinações diferentes dos mesmos campos.

### Fluxo 5 — Felipe explora o Sonar de Cobertura (visão geral, sem UJ dedicada no PRD)

1. Felipe abre a aba Sonar a qualquer momento.
2. Vê o mapa-mundi estilizado com países individuais: sem contorno/
   preenchimento (nunca escaneados), contorno roxo + preenchimento tênue
   (Missão ativa naquele país), contorno verde-campo + preenchimento tênue
   (Missão concluída, Relatório disponível).
3. Toca num país com contorno → resumo textual aparece (quantas Missões
   ativas/concluídas ali).
4. **Clímax:** de relance, Felipe entende exatamente em quais países sua
   rede de scouting está atuando e onde ainda não olhou — granularidade por
   país, não só por continente, orienta com precisão a próxima Missão a
   criar.
