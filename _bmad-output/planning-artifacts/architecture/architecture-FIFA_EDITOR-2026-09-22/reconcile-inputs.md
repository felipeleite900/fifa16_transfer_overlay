---
name: Reconcile Inputs — Central de Scout
type: reconciliation-report
purpose: 'Verificar o que da PRD/UX não aterrissou na ARCHITECTURE-SPINE.md'
created: '2026-09-30'
sources:
  - '{planning_artifacts}/architecture/architecture-FIFA_EDITOR-2026-09-22/ARCHITECTURE-SPINE.md'
  - '{planning_artifacts}/prds/prd-FIFA_EDITOR-2026-09-21/prd.md'
  - '{planning_artifacts}/ux-designs/ux-FIFA_EDITOR-2026-09-21/DESIGN.md'
  - '{planning_artifacts}/ux-designs/ux-FIFA_EDITOR-2026-09-21/EXPERIENCE.md'
---

# Reconcile Inputs — Central de Scout

## 1. Cobertura dos 11 FRs

Todos os 11 FRs do PRD (FR-1 a FR-11) têm uma linha correspondente no
`Capability → Architecture Map` da spine (linhas 244-252), cada uma apontando
para módulo(s) e AD(s) — inclusive FR-11 (Sonar), que aponta para
`scout::screens::sonar` sem AD dedicada (correto: é só uma tela de leitura,
sem invariante estrutural própria).

**Veredito: sem gap. Cobertura completa.**

## 2. As 6 Questões em Aberto do PRD (§8)

| # | Questão | Status na spine | Avaliação |
|---|---|---|---|
| 1 | Formato/local do arquivo de estado | **Resolvida** — JSON, write-through (AD-7), caminho `%LOCALAPPDATA%\FifaCompanion\scout\<pseudo_id>.json` (Structural Seed, linha 178) | Correto: é decisão estrutural, não de balanceamento — pertence à spine. |
| 2 | Fórmula de Fit Posicional | **Deferred** (linha 257) | Correto: conteúdo de balanceamento, mantido fora. |
| 3 | Fórmula de Qualidade + similaridade | **Deferred** (linha 256) | Correto. |
| 4 | Fórmula de custo | **Deferred** (linha 258) | Correto. |
| 5 | Troca de save com Missões pendentes | **Parcialmente resolvida, implicitamente** — AD-11 dá um pseudo-ID por save e nomeia o arquivo por esse ID, o que estruturalmente elimina o cenário de mistura entre saves (cada save só vê seu próprio arquivo) | **Gap — ver item 4 abaixo.** A spine não afirma isso explicitamente nem referencia a Questão em Aberto #5. |
| 6 | Risco de performance de leitura contínua de `CZUM`/`RrqT` em sessão longa | **Não mencionada em lugar nenhum** — nem resolvida, nem em Deferred | **Gap — ver Gap 2 abaixo.** |

## 3. Superfícies do EXPERIENCE.md vs. árvore de arquivos da spine

| Superfície (EXPERIENCE.md) | Arquivo na spine |
|---|---|
| Painel Scout (raiz) | `scout/mod.rs` |
| Aba Olheiros | `scout/screens/olheiros.rs` |
| Aba Missões | `scout/screens/missoes.rs` |
| Aba Relatórios | `scout/screens/relatorios.rs` |
| Aba Sonar | `scout/screens/sonar.rs` |
| Ficha de Jogador | `scout/screens/ficha_jogador.rs` |
| Formulário Nova Missão | `scout/screens/nova_missao.rs` |
| Painel de Seleção Geográfica | `scout/screens/selecao_geografica.rs` |
| Confirmação de Contratação | `scout/screens/confirmacao_contratacao.rs` |

**Veredito: sem gap nas 6 superfícies pedidas pelo usuário.** Todas presentes,
1:1.

Nota lateral (não pedida explicitamente, mas encontrada durante a checagem —
ver Gap 3): o componente **"Seletor de elenco"**, que o próprio EXPERIENCE.md
descreve como "mesmo componente... reaproveitado em dois momentos distintos"
(linha 86, usado em FR-7 dentro do Formulário Nova Missão e em FR-10 dentro
da Ficha de Jogador), não tem arquivo próprio na árvore — nem é mencionado
como exceção à convenção "uma tela por arquivo" (linha 132).

## 4. "Troca de save ativo com Missões pendentes" — obsolescência não sinalizada

`EXPERIENCE.md` linha 106 define um estado de UI explícito com aviso
"[ver mesmo assim] [descartar]" para esse cenário, marcado `[NOTE FOR PM]` e
`[ASSUMPTION]`, pendente da Questão em Aberto #5 do PRD.

AD-11 da spine (pseudo-ID de save lido da memória, um arquivo por save)
resolve estruturalmente a causa raiz do cenário: se cada save tem seu próprio
arquivo `<pseudo_id>.json`, ao trocar de save o Companion simplesmente
carrega (ou cria) o arquivo do save novo — nunca vê Missões de outro save
misturadas. O estado de aviso "ver mesmo assim / descartar" descrito no
EXPERIENCE.md deixa de fazer sentido como está escrito.

**A spine não declara isso em nenhum lugar** — nem no corpo do AD-11, nem em
Deferred, nem em nenhuma nota cruzada para o EXPERIENCE.md. Um leitor da
spine não tem como saber, sem fazer a inferência manual feita aqui, que esse
estado específico do EXPERIENCE.md ficou obsoleto e deveria ser reescrito
(ex: trocar o aviso por um estado simples "nenhuma Missão para este save
ainda" — o mesmo estado vazio já definido para "Nenhum Olheiro contratado").

**Confirmado: deveria haver uma nota mais explícita.** Ver Gap 1.

## 5. Contradições entre decisões técnicas da spine e o PRD

Nenhuma contradição real de comportamento encontrada. Uma divergência de
mecanismo vale nota:

- PRD §5 (linha 424-427) cita `identify_saves()` de `fifa16_search.py`
  (heurística por `mtime` do lado Python) como a referência para "save ativo
  identificado no momento".
- AD-11 da spine deliberadamente **rejeita** esse mecanismo (linha 119: "falha
  real da heurística de `mtime` usada pelo lado Python") e propõe
  identificação via memória (pseudo-ID de `GJUr.startdate` +
  manager + clube).

Isso é uma decisão técnica *correta e superior*, não uma contradição de
requisito — mas o PRD nunca é atualizado para refletir que o mecanismo de
referência mudou. É uma nota de rastreabilidade, não um problema funcional.

---

## Gaps Encontrados

### Gap 1 — [Severidade: Média] Estado obsoleto do EXPERIENCE.md não sinalizado

**O quê:** AD-11 (um arquivo por save, pseudo-ID via memória) elimina
estruturalmente o cenário "Troca de save ativo com Missões pendentes"
descrito em `EXPERIENCE.md` (linha 106), mas a spine não diz isso em lugar
nenhum.

**Risco:** Sem essa nota, o EXPERIENCE.md permanece com uma especificação de
UI (aviso "ver mesmo assim / descartar") que nunca será implementada,
gerando confusão na fase de `bmad-create-epics-and-stories` (uma story pode
ser criada para um estado que não existe mais) ou, pior, alguém implementa o
aviso desnecessariamente.

**Recomendação:** Adicionar uma linha explícita na spine (Deferred ou uma
nota dentro do AD-11) do tipo: *"Esta decisão torna obsoleto o estado 'Troca
de save ativo com Missões pendentes' do EXPERIENCE.md (linha 106) — o cenário
não pode mais ocorrer, pois cada save tem seu próprio arquivo de estado.
Recomenda-se atualizar o EXPERIENCE.md substituindo esse estado por um estado
vazio simples equivalente a 'Nenhum Olheiro/Missão para este save ainda'."*

### Gap 2 — [Severidade: Média] Questão em Aberto #6 (risco de performance) some sem rastro

**O quê:** A Questão em Aberto #6 do PRD (risco de FPS por leitura contínua
de `CZUM`/`RrqT` em sessão longa) não aparece em nenhuma AD, nem no
Capability Map, nem em Deferred. AD-4 mitiga o sintoma mais óbvio (scan
pesado não bloqueia a thread de render via `AsyncTask`), mas isso é diferente
de validar impacto cumulativo de FPS em sessão longa — a própria questão do
PRD já reconhece que a sessão 5 do `PROJECT_MEMORY.md` "não foi testada em
uso prolongado".

**Risco:** Fica sem dono. Diferente das fórmulas de Qualidade/Fit/custo (que
são corretamente Deferred porque são conteúdo de balanceamento fora do
escopo de uma spine de build-substrate), esta é uma questão de **validação
técnica empírica** — o mesmo tratamento dado a "Validação de `GJUr.startdate`"
(já presente em Deferred, linha 259). Omiti-la cria a impressão de que foi
resolvida ou de que nunca existiu.

**Recomendação:** Adicionar ao Deferred algo como: *"Validação empírica de
impacto em FPS durante sessão longa de scouting com `AsyncTask` ativo — PRD
Questão em Aberto #6. AD-4 mitiga bloqueio de thread de render, mas não
substitui medição real; primeira tarefa técnica ao integrar, semelhante à
validação de `GJUr.startdate` (AD-11)."*

### Gap 3 — [Severidade: Baixa] "Seletor de elenco" sem arquivo/módulo próprio

**O quê:** `EXPERIENCE.md` (linha 86) descreve o Seletor de elenco (lista de
jogadores do elenco atual) como *"mesmo componente... reaproveitado em dois
momentos distintos"* — como filtro de Jogador de Referência (FR-7, dentro do
Formulário Nova Missão) e como seletor de comparação (FR-10, dentro da Ficha
de Jogador). A árvore de arquivos da spine (linhas 216-239) não lista um
arquivo para esse componente, nem a convenção "uma tela por arquivo em
`scout/screens/`" (linha 132) menciona uma exceção para sub-componentes
reutilizáveis.

**Risco:** Sem um dono explícito, o componente tende a ser implementado duas
vezes (uma dentro de `nova_missao.rs`, outra dentro de `ficha_jogador.rs`),
contradizendo a intenção de reuso que o próprio EXPERIENCE.md deixa
explícita.

**Recomendação:** Ou (a) adicionar `scout/screens/seletor_elenco.rs` à árvore
de arquivos (mesmo padrão de `selecao_geografica.rs`, que também é um
sub-painel reutilizado a partir do formulário), ou (b) adicionar uma frase à
Consistency Conventions explicando onde sub-painéis compartilhados (não
top-level de uma aba) devem viver.

### Gap 4 — [Severidade: Baixa] Estado de UI persistente (densidade de Relatório, última aba) sem lugar na spine

**O quê:** `EXPERIENCE.md` exige explicitamente dois comportamentos de
persistência de UI entre sessões:
- "Densidade (Tabular vs. Cards) é uma preferência persistente do usuário...
  não reseta a cada abertura do painel" (linhas 82-83).
- "Painel abre na última aba usada (ou Olheiros, se primeira vez)" (Fluxo 1,
  linha 149).

O ER diagram e a Structural Seed da spine (linhas 184-212) só modelam
entidades de domínio (`Olheiro`, `Missao`, `Relatorio`, `JogadorEncontrado`).
AD-7 (write-through) enumera exemplos de mutação apenas de domínio
("contratar Olheiro, criar Missão, arquivar Relatório"), sem mencionar
preferências de UI.

**Risco:** Baixo mas real — se ninguém notar, essas duas preferências podem
ser implementadas como estado voláteis (`static`/`AtomicBool` em memória do
processo overlay) que se perdem a cada reinjeção da DLL, quebrando o
comportamento explicitamente prometido no EXPERIENCE.md.

**Recomendação:** Nota simples em `scout::persistence`/`scout::state`
reconhecendo que o arquivo JSON write-through também carrega um pequeno
bloco de preferências de UI (`ultima_aba`, `densidade_relatorio`), não só
entidades de domínio. Não exige uma AD nova — só uma linha a mais na
Structural Seed ou no ER diagram.

---

## Nota Final

Nenhum dos 4 gaps é crítico o suficiente para bloquear a fase de
`bmad-create-epics-and-stories`: a cobertura estrutural dos 11 FRs está
completa, as 4 fórmulas de balanceamento estão corretamente em Deferred, e
todas as 6 superfícies pedidas têm arquivo correspondente. Os gaps
encontrados são lacunas de **rastreabilidade e sinalização explícita** (algo
que a spine resolveu implicitamente mas não declarou, ou algo que
desapareceu silenciosamente entre PRD/UX e spine) — recomenda-se
incorporá-los como pequenos ajustes de texto na spine antes de seguir para
épicos/stories, em vez de reabrir a fase de arquitetura.
