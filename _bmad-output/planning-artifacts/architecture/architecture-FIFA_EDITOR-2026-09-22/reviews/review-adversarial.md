# Review Adversarial — Pares de Implementação Divergentes

Escopo desta review: não julgar se as ADs são "boas ideias" (isso já foi
feito em `review-rubric.md`, que é majoritariamente elogioso), mas atacá-las
como um adversário — para cada AD-1 a AD-13, construir dois cenários de
implementação hipotéticos, um nível abaixo da spine (duas stories/sessões
futuras), que obedecem a Rule escrita ao pé da letra e ainda assim produzem
artefatos incompatíveis entre si (formato de dado diferente, dono ambíguo de
um campo, condição de corrida, ou API pública divergente de um tipo
genérico). Não aceito nenhuma Rule pelo valor de face; tentei ativamente
quebrar cada uma.

## Veredito geral

A spine tem uma fraqueza estrutural real e recorrente: **ela fixa muito bem
os limites *entre* as 4 camadas (AD-1/AD-2/AD-3), mas quase não fixa nada
sobre o grafo de chamadas *dentro* da camada de domínio** (`state` ↔
`search` ↔ `quality` ↔ `persistence` são tratados como um bloco único, sem
regra de quem chama quem) — e essa lacuna única se propaga em cascata para
pelo menos três outras ADs (quem monta o `Relatorio` final, quem escreve
`ui_prefs`, e uma contradição literal com a própria AD-13). Encontrei também
duas contradições diretas dentro do próprio documento (AD-12 vs. o ER
diagram; AD-13 vs. AD-1/AD-2), uma condição de corrida real e não coberta no
write-through (AD-7), e o buraco de API pública do `AsyncTask<T>` já
antecipado no brief (AD-4). Nenhum desses pontos é cosmético — todos geram
dois artefatos concretos, ambos "corretos" perante o texto da Rule, que não
funcionam juntos.

---

## AD-1 — Dependência unidirecional entre camadas

**Achado central (H1, severidade ALTA):** a Rule fixa apenas a ordem entre
as 4 *camadas* da lista do Design Paradigm — não diz nada sobre quem, *dentro*
da camada de Domínio, pode chamar quem. `scout::state`, `scout::search`,
`scout::quality` e `scout::persistence` são citados juntos como uma única
camada ("Domínio — state, search, quality, persistence"), mas a Rule
("uma camada só pode chamar a camada imediatamente abaixo dela") não impede
`persistence` de chamar `search`, nem `search` de chamar `persistence`
diretamente sem passar por `state` — mesmo que o Structural Seed mostre um
grafo mais restrito (`Screens → State`, `State → Persist`, `Search → Repo`,
`Quality → Repo`, sem nenhuma seta apontando para `Persist` além de
`State → Persist`).

**Par divergente:**
- **Sessão A** implementa `scout::screens::relatorios` chamando
  `scout::persistence::salvar_preferencia_ui("densidade", "cards")`
  *diretamente* da tela, porque "densidade" é uma preferência de UI, não uma
  entidade de domínio, e a tela lê a Rule do AD-1 como permitindo isso — afinal
  `persistence` está na mesma camada ("Domínio") que `screens` teria
  permissão de chamar segundo a leitura literal ("a camada imediatamente
  abaixo").
- **Sessão B** implementa a mesma feature roteando *tudo* por `scout::state`
  primeiro (mesmo preferências de UI), porque essa sessão leu o Structural
  Seed como normativo e assumiu que só `state.rs` tem permissão de chamar
  `persistence.rs`.

Ambas obedecem ao texto literal do AD-1. O resultado é dois pontos de
entrada para `persistence.rs` com contratos diferentes (uma função solta
`salvar_preferencia_ui(chave, valor)` vs. um método em `ScoutState` que
recebe o objeto inteiro), e potencialmente dois caminhos de escrita
concorrentes no mesmo arquivo (ver H6, AD-7).

**Fix:** a spine precisa de uma frase explícita fixando o grafo de chamadas
*dentro* da camada de Domínio — ex.: "`persistence` só é chamado por
`state`; `search`/`quality` nunca chamam `persistence` diretamente; toda
mutação, de domínio ou de UI, passa por `scout::state` antes de chegar em
`persistence`." Isso também resolveria H3 e H6 abaixo, que têm a mesma causa
raiz.

---

## AD-2 — `save_repo` é a única porta para `memscan`/`fifa_db`

A Rule em si é bem fechada ("`save_repo.rs` é o único módulo autorizado a
chamar `memscan`/`fifa_db`/`pointer_scan`"), mas ela depende de AD-1 para
impedir que uma *tela* pule direto para `save_repo` sem passar pelo domínio.
Achei exatamente essa violação — ver **H2 em AD-13** abaixo, que é uma
contradição direta e concreta dentro do próprio documento, não uma
divergência hipotética.

---

## AD-3 — `save_repo` é burro; filtros e cálculo vivem em `search`/`quality`

**Achado central (H3, severidade CRÍTICA):** a Rule diz onde cada cálculo
*vive* (5 filtros em `search`, Qualidade/Fit/similaridade em `quality`), mas
não diz **quem monta o `Relatorio` final** — e o Structural Seed torna isso
pior, não melhor: o diagrama mostra `Search --> Repo` e `Quality --> Repo`
como duas setas *independentes e paralelas*, sem nenhuma seta entre `Search`
e `Quality`. Isso é exatamente o cenário citado no brief: "quem decide o
valor de Qualidade de um Relatório fica ambíguo entre `scout::search` e
`scout::quality`?" — a resposta da spine, lida literalmente, é "nenhum dos
dois tem permissão documentada de chamar o outro".

**Par divergente:**
- **Sessão A** implementa `scout::search::executar_missao()` como o
  orquestrador completo: ele filtra os candidatos (sua responsabilidade por
  AD-3), e *também* chama internamente `scout::quality::calcular_qualidade(...)`
  para montar e devolver o `Relatorio` já pronto (com `qualidade` preenchido)
  — assumindo que "quality → repo" no diagrama é só para o caso de
  `quality` precisar reler dados brutos por conta própria em outro fluxo
  (ex.: recalcular ao abrir a Ficha de Jogador), não que `search` não possa
  chamá-lo.
- **Sessão B** implementa o inverso: `scout::search` devolve apenas
  `Vec<PlayerFound>` (crus, filtrados, sem Qualidade calculada) para
  `scout::state`, e é `scout::quality::gerar_relatorio(missao, candidatos)`
  quem monta o `Relatorio` final e o entrega para `state` persistir — porque
  essa sessão leu "cálculo de Qualidade... vive em `scout::quality`" como
  "quality é quem produz o Relatorio", não "quality só expõe uma função pura
  de cálculo que outro módulo chama".

Ambas as sessões obedecem ao texto do AD-3 ao pé da letra. O resultado é
dois contratos de função completamente diferentes entre `search` e
`quality` (quem depende de quem, qual módulo tem o `use` do outro, qual
função é a orquestradora pública chamada por `scout::state`) — se as duas
sessões forem implementadas por pessoas diferentes (ou pela mesma pessoa em
dias diferentes sem reler o código), o build não fecha ou fecha com um dos
dois módulos morto/duplicado.

**Fix:** adicionar uma frase ao AD-3 (ou uma AD nova) nomeando o
orquestrador: ex. "`scout::search::executar_missao()` é o único ponto que
monta o `Relatorio` completo; ele chama `scout::quality` internamente para
preencher `qualidade`/`fit_posicional`/`similaridade` antes de devolver o
`Relatorio` pronto para `scout::state` persistir. `scout::quality` nunca
chama `scout::search`." E adicionar a seta `Search --> Quality` faltante no
Structural Seed.

---

## AD-4 — `AsyncTask<T>` genérico

**Achado central (H4, severidade ALTA — já antecipado no brief).** A Rule
diz *que* `AsyncTask<T>` deve ser usado, mas não define a API pública do
tipo além de "encapsula `Arc<Mutex<TaskState<T>>>` + `Arc<AtomicBool>`".
Dois problemas concretos de divergência:

1. **Estados terminais.** `TaskState<T>` não tem suas variantes listadas.
   - **Sessão A:** `enum TaskState<T> { Idle, Running, Done(T) }`, e trata
     erro fazendo `T = Result<Vec<Player>, SaveRepoError>` — ou seja, o
     estado `Done` sempre existe, mas carrega um `Result` por dentro.
   - **Sessão B:** `enum TaskState<T> { Idle, Running, Done(T), Failed(SaveRepoError) }`
     — erro é um estado irmão de `Done`, não embutido em `T`.
   Ambas satisfazem "encapsula `TaskState<T>`". Mas qualquer código
   consumidor (`scout::screens::missoes` fazendo `match task.poll() { ... }`)
   escrito contra uma API não compila contra a outra — não é um detalhe de
   implementação interna, é a **API pública** que todo `screens::*` que usa
   `AsyncTask` vai importar.

2. **Contrato de leitura do resultado.** Nada diz se `poll()`/`state()`
   devolve uma referência (`&TaskState<T>`, exigindo `T: Clone` para tirar o
   valor de dentro do Mutex) ou consome o valor (`take() -> Option<T>`,
   estado só pode ser lido uma vez). Isso conflita diretamente com AD-5: se
   `T` inclui um `SaveRepoError` (opção da Sessão A acima), e
   `scout::screens` precisa "tratar cada variante explicitamente" toda vez
   que o painel renderiza (a cada frame, já que ImGui é modo imediato), uma
   API que **consome** o resultado na primeira leitura (`take()`) faz o erro
   desaparecer do estado depois do primeiro frame em que foi exibido — a
   segunda sessão de implementação, que espera poder reler o estado em todo
   frame (`&TaskState<T>` por referência), quebra completamente se a
   primeira sessão implementou `take()`-semantics.

**Fix:** a spine precisa fixar, mesmo que em uma frase, a assinatura pública
mínima: nome e variantes de `TaskState<T>` (incluindo o estado de erro como
variante irmã de `Done`, não embutido em `T`, para não colidir com AD-5), e
se a leitura é por referência (idempotente, seguro para chamar a cada
frame) ou por consumo. Sem isso, `async_task.rs` — que é o arquivo mais
citado/reaproveitado de toda a árvore — tem uma API que dois devs
plausivelmente implementariam de formas mutuamente incompatíveis.

---

## AD-5 — Erros do `save_repo` são tipados

A Rule em si é forte e enforceable (`Result<T, SaveRepoError>` no retorno,
compilador ajuda). O único buraco real aqui é o que já foi descrito em H4:
a Rule não diz onde `SaveRepoError` "mora" quando a operação é assíncrona —
dentro de `T` do `AsyncTask<T>` ou como estado irmão. Não abro um finding
novo para isso; é o mesmo buraco de H4, só que visto do lado do consumidor.

---

## AD-6 — Navegação de tela é uma pilha

**Achado central (H5, severidade ALTA).** A Rule descreve push/pop, mas
nunca resolve dois casos de borda que dois implementadores resolveriam de
formas diferentes e incompatíveis:

1. **Pop no último nível.** A pilha começa com o quê — vazia, ou já contém
   a aba raiz como elemento 0? O Capability Map (linha 253) atribui FR-1
   ("abrir/fechar painel") a AD-6, então a spine claramente pretende que
   fechar o painel seja modelado através da pilha — mas a Rule nunca diz
   como.
   - **Sessão A** modela a aba ativa como `stack[0]` permanente (nunca
     poppável); `pop()` chamado com `stack.len() == 1` é tratado como
     no-op, e fechar o painel é um `bool is_open` totalmente separado da
     pilha.
   - **Sessão B** modela a aba ativa como `stack[0]` poppável igual a
     qualquer outra tela; `pop()` em pilha de tamanho 1 esvazia a pilha, e
     `scout::mod` interpreta "pilha vazia" como "fechar o painel" — sem
     `bool` adicional.
   Ambas obedecem "voltar = pop, sempre a mesma operação em qualquer ponto
   do app". Só uma delas faz FR-1 funcionar sem um campo extra de estado
   que a spine nunca menciona.

2. **Fechar e reabrir o painel.** `EXPERIENCE.md` (Fluxo 1, linha 149) exige
   "painel abre na última aba usada" — ou seja, ao reabrir, a navegação
   *não* deveria resumir de dentro de uma tela empurrada (ex.:
   `ficha_jogador`), deveria voltar à aba de topo. AD-6 nunca diz se fechar
   o painel faz `stack.clear()` + `push(ultima_aba)`, ou se preserva a
   pilha intacta entre fechamentos (deixando o usuário reabrir e cair
   exatamente onde estava, inclusive dentro de uma Ficha de Jogador aberta).
   Duas sessões plausíveis divergem exatamente nisso, e o EXPERIENCE.md
   citado como fonte da spine sugere um comportamento que o AD-6 não
   garante.

3. **(Secundário, severidade BAIXA)** Profundidade máxima: `EXPERIENCE.md`
   promete "no máximo dois níveis", mas isso é só prosa de UX — não há
   nenhum mecanismo em AD-6 (assert, tipo, ou regra) que impeça um futuro
   fluxo (ex.: `ficha_jogador → seletor_elenco → ficha_jogador de outro
   jogador → ...`) de empilhar indefinidamente.

**Fix:** decidir e nomear explicitamente (a) se a pilha nunca fica vazia
(elemento raiz fixo) e o que abre/fecha o painel é um campo separado, e (b)
o que acontece à pilha no ciclo fechar→reabrir. Se quiser manter a garantia
de profundidade 2, tornar isso mecânico (ex.: `push` recusa se
`stack.len() >= 2` e loga aviso) em vez de só prosa de UX.

---

## AD-7 — Escrita write-through, incluindo `ui_prefs`

**Achado central (H6, severidade CRÍTICA — condição de corrida real).** A
Rule diz "toda mutação... dispara reescrita síncrona e imediata do arquivo
JSON inteiro", mas nunca nomeia **um único ponto de serialização
protegido por um único lock** que medeie todas as escritas. Isso importa
porque a spine tem, ela mesma, pelo menos dois escritores concorrentes
possíveis:

- O `AsyncTask` de busca de Missão (AD-8) roda em **thread separada** e
  "grava o resultado via write-through assim que a thread termina" — ou
  seja, um write-through disparado de uma thread de background.
- Uma mutação de `ui_prefs` (trocar densidade Tabular/Cards, trocar de aba)
  disparada pela **thread de render** (main thread), no meio do frame em
  que a thread de background do parágrafo anterior também está terminando.

**Par divergente:**
- **Sessão A** implementa cada ponto de mutação com seu próprio padrão
  "ler arquivo do disco → aplicar minha mudança no struct → serializar →
  escrever arquivo inteiro de volta", chamado independentemente pela thread
  de render (para `ui_prefs`) e pela thread do `AsyncTask` (para o
  `Relatorio` concluído) — sem nenhum mutex compartilhado entre os dois
  caminhos, porque a Rule não pede um.
- **Sessão B** implementa um único `Arc<Mutex<ScoutState>>` global que
  *todo* mutador (render thread ou thread de background) precisa travar
  antes de mutar e escrever, garantindo serialização real.

Ambas obedecem à letra do AD-7 ("toda mutação... dispara reescrita
síncrona"). Só a Sessão B é livre de *lost update*: na Sessão A, se a thread
de render lê o arquivo, o `AsyncTask` termina e escreve sua versão
(contendo o novo `Relatorio`), e a thread de render escreve a sua versão
*depois* (baseada na leitura antiga, sem o `Relatorio` novo) — o
`Relatorio` recém-concluído é silenciosamente perdido do disco até a
próxima mutação de domínio re-serializar tudo. Esse é precisamente o tipo
de bug que só aparece em produção, de forma intermitente, dependendo de
timing — o pior tipo de bug para um projeto hobby sem suíte de testes.

**Fix:** nomear explicitamente o mecanismo de exclusão mútua — ex.: "todo
write-through passa por um único `Arc<Mutex<ScoutStateFile>>` mantido em
`scout::persistence`; tanto mutações de domínio quanto de `ui_prefs`, seja
qual for a thread de origem, travam esse mutex antes de ler-modificar-
escrever o arquivo." Isso também fecha, de quebra, o buraco H1 (força que
toda escrita passe por um ponto nomeado único).

---

## AD-8 — Missão: busca só executa na conclusão

**Achado (H7, severidade MÉDIA-ALTA).** Dois pontos moles:

1. **Gatilho "painel reaberto" é polling ou edge-trigger?** A Rule diz
   "quando o painel é reaberto e `read_current_date()` indica que o prazo
   já passou, então o `AsyncTask`... é disparado". Isso descreve um evento
   discreto (reabertura), não um estado contínuo.
   - **Sessão A** checa a condição de prazo **a cada frame** enquanto o
     painel está aberto (não só no instante da reabertura) — então, se o
     usuário abre o painel *antes* do prazo vencer e simplesmente o deixa
     aberto enquanto o relógio da carreira avança (ex.: jogando partidas com
     o painel no fundo), a Missão dispara assim que o prazo vira, mesmo sem
     um evento de "reabertura".
   - **Sessão B** implementa literalmente "ao reabrir" como uma transição de
     borda (`estava_fechado && agora_aberto`) e só checa o prazo *nesse
     instante* — se o usuário nunca fecha e reabre o painel depois que o
     prazo vence, a Missão nunca dispara até o próximo ciclo fechar→abrir.
   Ambas obedecem ao texto. O comportamento visível ao usuário é
   radicalmente diferente (Missão "trava" indefinidamente na Sessão B se o
   painel ficar aberto o tempo todo).

2. **Guard contra redisparo.** Nada impede que, se o painel for fechado e
   reaberto *de novo* antes do primeiro `AsyncTask` da Missão terminar
   (busca pesada, potencialmente minutos), a checagem de "prazo já passou"
   rode de novo e dispare um **segundo** `AsyncTask` para a mesma Missão. A
   Rule não menciona nenhum campo tipo `Missao.status = EmExecucao` que
   sirva de guard. Uma sessão que adiciona esse campo e outra que não
   adiciona são ambas "corretas" pelo texto do AD-8, mas só uma evita scan
   duplicado da CZUM para a mesma Missão.

**Fix:** especificar que a checagem acontece só na transição borda
fechado→aberto (evento único, não polling contínuo) **e** nomear o campo de
estado (`Missao.status`) que impede redisparo enquanto um `AsyncTask` já
está em `Running` para aquela Missão.

---

## AD-9 — Fila sequencial entre Missões vencidas

Este AD já foi marcado como "não enforceable pelo texto" em
`review-rubric.md` (finding medium) — concordo com esse diagnóstico e não o
repito aqui. O que acrescento, especificamente sob a lente adversarial de
*pares divergentes*:

**Achado (H8, severidade MÉDIA).** Mesmo assumindo que ambas as sessões
implementem *algum* mecanismo de serialização (fechando o buraco já
apontado no rubric), a Rule não define **a ordem** de processamento quando
mais de uma Missão vence simultaneamente.
- **Sessão A** processa por `prazo_estimado` crescente (a que venceu há
  mais tempo primeiro).
- **Sessão B** processa por ordem de criação da Missão (`criada_em`
  crescente).
Ambas são "uma fila simples, nunca em paralelo" — a Rule está satisfeita
nos dois casos —, mas o usuário vê Relatórios prontos em ordens diferentes
dependendo de qual sessão implementou a fila, o que é visível na UI (aba
Missões/Relatórios mostra indicador de "novo" um de cada vez).

**Fix:** nomear o critério de ordenação (ex.: "FIFO por `prazo_estimado`
ascendente; em empate, por `criada_em`").

---

## AD-10 — `AsyncTask`s de preocupações diferentes são independentes

**Achado (H9, severidade MÉDIA — exatamente o cenário pedido no brief).** A
fronteira entre "isso é uma Missão" (entra na fila sequencial do AD-9) e
"isso é uma preocupação diferente" (roda livre e paralelo, por AD-10) é
definida por **categoria de domínio** ("execução de busca de Missão"), não
por **custo computacional** ("varre a CZUM inteira, ~32k registros"). O
`Prevents` do próprio AD-9 diz que o problema a evitar é "múltiplos scans
pesados de CZUM rodando ao mesmo tempo, competindo por CPU/memória" — um
argumento de *recurso*, não de *categoria de domínio*.

**Par divergente (prospectivo, mas plausível dado o roadmap):** hoje só
existe um consumidor de scan pesado de CZUM (busca de Missão). Mas o Sonar
de Cobertura (FR-11) é hoje "somente leitura" sobre dados já persistidos —
nada impede uma versão futura de FR-11 (ou qualquer outra feature) precisar
de um scan pesado independente da CZUM para, por exemplo, recalcular
cobertura em tempo real.
- **Sessão A** (lendo AD-9 como regra de *categoria*) implementa esse novo
  scan pesado como um `AsyncTask` totalmente independente, livre por
  AD-10, porque "não é execução de busca de Missão".
- **Sessão B** (lendo o `Prevents` do AD-9 como a intenção real, que é sobre
  *recursos*) insiste em enfileirar esse novo scan pesado na mesma fila do
  AD-9, porque senão o `Prevents` original ("competindo por CPU/memória")
  fica furado.
Ambas as leituras são defensáveis pelo texto; a spine não resolve o
conflito entre "fronteira por categoria de domínio" (o que o Rule diz
literalmente) e "fronteira por custo computacional" (o que o Prevents
realmente quer evitar). Isso é uma bomba-relógio de baixo risco hoje (só um
consumidor pesado existe) mas alto risco assim que uma segunda feature de
scan pesado for proposta.

**Fix:** reescrever o `Prevents`/Rule do AD-9 para deixar explícito que a
serialização é por **recurso compartilhado** (qualquer operação que varra a
CZUM inteira), não por categoria de domínio — ou, alternativamente, aceitar
e documentar que o escopo é deliberadamente restrito a Missões por agora e
registrar em Deferred que qualquer scan pesado futuro fora de Missão
precisa revisitar esta AD.

---

## AD-11 — Pseudo-ID do save ativo

**Achado (H10, severidade ALTA — a versão mais concreta do "buraco de
formato" pedido no brief).** A Rule define os *componentes* do pseudo-ID
(`GJUr.startdate` + `mPrV.firstname`/`surname` + `mPrV.clubteamid`), mas não
o **formato de serialização exato** — e esse pseudo-ID vira literalmente o
**nome de arquivo** no disco (`<pseudo_id>.json`), o que torna a ambiguidade
muito mais perigosa do que uma ambiguidade de campo JSON comum.

**Par divergente:**
- **Sessão A** implementa `pseudo_id = format!("{}_{}_{}_{}", startdate,
  firstname, surname, clubteamid)` — concatenação crua, sem sanitização.
  Nomes de manager com acentos, espaços, ou caracteres reservados do
  Windows (`\ / : * ? " < > |`) produzem um nome de arquivo inválido ou um
  crash de `std::fs::File::create`.
- **Sessão B** implementa `pseudo_id = format!("{:x}", hash_sha256(...))`
  — hash hexadecimal, sempre um nome de arquivo válido, mas
  **não-determinístico entre as duas sessões** (uma gera
  `20260101_Felipe_Silva_5.json`, a outra gera
  `a91f3e...c02.json` para o mesmo save) — arquivos de estado já gravados
  por uma sessão não são reconhecidos pela outra, silenciosamente perdendo
  todas as Missões/Relatórios/Olheiros já persistidos na primeira
  implementação assim que o código migrar de uma convenção para outra.

Ambas obedecem "identificador... é um pseudo-ID composto, lido inteiramente
da memória". Nenhuma viola a Rule. O resultado é dois formatos de nome de
arquivo mutuamente incompatíveis, um dos quais pode nem funcionar em todos
os casos (nomes de manager com caracteres especiais).

**Fix:** fixar o formato de serialização exato (separador, ordem dos
campos, e — criticamente — a estratégia de sanitização/encoding para
caracteres inválidos de nome de arquivo Windows vindos de `firstname`/
`surname`, ex.: "hash SHA-256 do pseudo-ID concatenado, formatado em hex
lowercase, sempre — nunca os componentes crus no nome de arquivo").

---

## AD-12 — IDs de entidade são UUID v4

**Achado (H11, severidade ALTA — contradição literal dentro do próprio
documento, não uma divergência hipotética).** O texto do AD-12 (`Binds`)
lista explicitamente **quatro** structs que recebem UUID: "`Olheiro`,
`Missao`, `Relatorio`, jogador encontrado". Mas o ER diagram, duas seções
abaixo no mesmo arquivo (linha 208-212), modela `JOGADOR_ENCONTRADO` com
**apenas** `int playerid` — nenhum campo `Uuid id`.

**Par divergente concreto, cada lado lendo uma parte diferente do mesmo
documento como autoritativa:**
- **Sessão A** lê o `Binds` do AD-12 e adiciona
  `id: Uuid` à struct `JogadorEncontrado`, gerando um novo UUID por
  registro encontrado a cada execução de Missão.
- **Sessão B** lê o ER diagram (que é o artefato mais "visual"/citado na
  Structural Seed) e implementa `JogadorEncontrado { playerid: i32,
  atributos: AtributosParciais, fit_posicional: FitPosicional }` sem campo
  `id` — usando `playerid` como chave natural.

Isso não é uma leitura forçada — é uma contradição real, palavra-a-palavra,
entre duas seções do mesmo `ARCHITECTURE-SPINE.md`. Qualquer geração
automática de código/schema a partir do ER diagram (comum em fases
posteriores) vai divergir silenciosamente do texto do AD-12.

**Fix:** escolher um lado e corrigir o outro. Dado que `JogadorEncontrado`
tem uma chave natural óbvia (`playerid`, o ID nativo do FIFA) e não
participa de referências cruzadas por UUID em nenhum outro lugar da spine
(diferente de `Missao.olheiro_id`/`Relatorio.missao_id`), a correção mais
barata é remover "jogador encontrado" da lista de `Binds` do AD-12 e deixar
uma nota explícita: "`JogadorEncontrado` é identificado por `playerid`
(chave natural do FIFA), não recebe `Uuid` próprio."

---

## AD-13 — Seletor de elenco compartilhado

**Achado (H2, severidade CRÍTICA — viola AD-1/AD-2 no texto da própria
spine).** A Rule do AD-13 diz: "expondo a lista do elenco (via
`save_repo::read_squad_players`, síncrono conforme AD-4)". Mas
`seletor_elenco.rs` vive em `scout::screens::seletor_elenco` — **camada
UI**, segundo a própria árvore de arquivos (linha 242, dentro de
`screens/`). AD-1 proíbe explicitamente "uma tela acessando `save_repo` sem
passar pelo domínio" e AD-2 diz que `save_repo` só é chamado por
`scout::*` (domínio), nunca por `screens::*`. O texto do AD-13, lido
literalmente, instrui a violar os dois.

**Par divergente:**
- **Sessão A** implementa `AD-13` ao pé da letra: `seletor_elenco.rs`
  (tela) chama `save_repo::read_squad_players()` diretamente — mais simples,
  menos boilerplate, e é exatamente o que o texto do AD-13 descreve.
- **Sessão B** implementa `AD-1`/`AD-2` ao pé da letra: `seletor_elenco.rs`
  chama uma função de fachada em `scout::state` (ex.:
  `scout::state::listar_elenco_atual()`) que por sua vez chama
  `save_repo::read_squad_players()` — porque essa sessão trata AD-1/AD-2
  como regras de nível mais alto (fronteira de camada) que têm precedência
  sobre a conveniência descrita em AD-13.

Ambas as sessões estão "certas" segundo uma AD e "erradas" segundo outra —
é uma contradição real dentro do documento, não uma ambiguidade de
interpretação. Isso também é o único ponto na spine inteira onde a regra
"tela → domínio → repo, nunca pula camada" tem uma exceção nomeada — e essa
exceção nunca é declarada como tal.

**Achado secundário (H13, severidade MÉDIA):** independente do ponto
acima, o AD-13 também não resolve se `seletor_elenco` participa da pilha do
AD-6 (`ScoutScreen::SeletorElenco(contexto)`) ou é um overlay de estado
local mantido separadamente por cada tela hospedeira (`nova_missao.rs` e
`ficha_jogador.rs` cada uma com seu próprio `bool mostrando_seletor`). Se
for a segunda opção, o "componente único" do AD-13 compartilha só a função
de *renderização*, mas duplica exatamente o gerenciamento de estado que o
`Prevents` do AD-13 diz querer evitar ("duas implementações divergentes da
mesma lista") — só que agora a duplicação é do controle de
abrir/fechar/voltar, não da lista em si. Isso também quebra a consistência
do botão "cancelar" do gamepad (Interaction Primitives: "botão de cancelar
fecha modais/volta uma tela"), que espera uma pilha única para saber para
onde voltar.

**Fix:** (a) declarar AD-13 como exceção nomeada e explícita a AD-1/AD-2
("único caso na spine onde uma tela chama `save_repo` diretamente, porque
lista de elenco é leitura pura sem regra de domínio" — ou, preferível,
apenas roteá-lo por `scout::state` como qualquer outra tela, eliminando a
exceção); (b) decidir e declarar se `seletor_elenco` é uma variante de
`ScoutScreen` na pilha do AD-6 ou não.

---

## Achado sistêmico — formato JSON de `Date`

**Achado (H12, severidade ALTA, atravessa AD-7/AD-11/AD-12/Consistency
Conventions).** A tabela de Consistency Conventions diz: "Datas: reaproveita
o formato já `[ADOPTED]` de `GJUr.currdate` (`YYYYMMDD` como inteiro,
convertido para um tipo `Date` interno do domínio)." Essa frase descreve a
**leitura da memória do jogo** (de onde vem o inteiro `YYYYMMDD`) e a
**conversão para um tipo interno**, mas nunca diz qual é a **forma
serializada em JSON** desse tipo `Date` interno quando ele é gravado no
arquivo de estado via write-through (AD-7) — e `Date` aparece em pelo menos
três campos persistidos: `Missao.criada_em`, `Missao.prazo_estimado`, e
implicitamente em qualquer timestamp de `Relatorio`/`ui_prefs` futuro.

**Par divergente:**
- **Sessão A** define `struct Date(i32)` (newtype sobre o inteiro
  `YYYYMMDD` cru) com `#[derive(Serialize, Deserialize)]` — serializa como
  `"prazo_estimado": 20261015` no JSON.
- **Sessão B** define `struct Date { year: u16, month: u8, day: u8 }`
  (já decomposto, mais ergonômico para exibir "pronto em ~N dias" na UI) —
  serializa como `"prazo_estimado": {"year":2026,"month":10,"day":15}`.
- **Sessão C** implementa um `Serialize`/`Deserialize` customizado que
  emite string ISO-8601 — `"prazo_estimado": "2026-10-15"`.

As três leem a mesma frase da Consistency Conventions como satisfeita
("convertido para um tipo `Date` interno do domínio" não fixa a forma
serializada). Se `persistence.rs` for implementado numa sessão e qualquer
código que precise *ler* esse campo de volta (ex.: uma ferramenta de
migração, ou simplesmente uma segunda pessoa reimplementando
`scout::state::Date` sem saber que já existe uma versão anterior gravada em
disco) escolher uma forma diferente, o `serde_json::from_str` falha ao
carregar qualquer arquivo de estado já existente — perda de dados silenciosa
ou pane no carregamento do painel.

**Fix:** fixar explicitamente a forma serializada de `Date` na Consistency
Conventions — ex.: "`Date` serializa como o inteiro `YYYYMMDD` cru em JSON
(`#[serde(transparent)]` sobre `i32`), nunca como struct aninhada ou string
ISO — mantém paridade 1:1 com o formato já lido de `GJUr.currdate`,
evitando conversão com perda ou ambiguidade de fuso/formato."

---

## Resumo dos Achados

| # | AD | Severidade | Resumo |
|---|---|---|---|
| H1 | AD-1 | **Alta** | Grafo de chamadas *dentro* da camada de Domínio (`state`/`search`/`quality`/`persistence`) não é fixado — só a ordem entre as 4 camadas é. Causa raiz de H3 e H6. |
| H2 | AD-2 / AD-13 | **Crítica** | AD-13 instrui `seletor_elenco` (camada UI) a chamar `save_repo` diretamente — contradiz literalmente AD-1/AD-2 no mesmo documento. |
| H3 | AD-3 | **Crítica** | Quem monta o `Relatorio` final (chama Qualidade a partir de Search, ou o inverso) não é definido; Structural Seed nem mostra uma seta entre `Search` e `Quality`. |
| H4 | AD-4 | **Alta** | API pública de `TaskState<T>` (variantes, erro embutido em `T` vs. estado irmão, leitura por referência vs. consumo) não é fixada — colide com AD-5. |
| H5 | AD-6 | **Alta** | Comportamento da pilha vazia (fecha o painel? é no-op?) e do ciclo fechar→reabrir (preserva profundidade ou reseta para a aba de topo, como `EXPERIENCE.md` sugere) não são definidos. |
| H6 | AD-7 | **Crítica** | Nenhum lock único nomeado medeia todas as escritas write-through; thread de background (conclusão de Missão) e thread de render (mudança de `ui_prefs`) podem colidir em *lost update* real. |
| H7 | AD-8 | **Média-Alta** | "Painel reaberto" como polling contínuo vs. evento de borda único produz comportamentos de disparo de Missão radicalmente diferentes; falta guard contra redisparo de `AsyncTask` já em andamento. |
| H8 | AD-9 | **Média** | Critério de ordenação da fila entre Missões vencidas simultaneamente não é definido (por prazo vs. por criação). |
| H9 | AD-10 | **Média** | Fronteira "Missão" (serializada) vs. "outra preocupação" (paralela) é por categoria de domínio, não por recurso compartilhado — um futuro scan pesado fora de Missão furaria o próprio `Prevents` do AD-9. |
| H10 | AD-11 | **Alta** | Formato de serialização do pseudo-ID (concatenação crua vs. hash) não é fixado, e o pseudo-ID vira nome de arquivo — risco real de caracteres inválidos de nome de arquivo Windows vindos de `firstname`/`surname`. |
| H11 | AD-12 | **Alta** | Contradição literal dentro do documento: `Binds` do AD-12 lista "jogador encontrado" como tendo UUID; o ER diagram modela `JOGADOR_ENCONTRADO` sem campo `id`. |
| H12 | Cross-cutting (AD-7/12/Conventions) | **Alta** | Forma serializada em JSON do tipo `Date` (inteiro cru vs. struct vs. string ISO) nunca é fixada, apesar de ser persistida em múltiplos campos via write-through. |
| H13 | AD-13 | **Média** | Não é definido se `seletor_elenco` é uma variante de `ScoutScreen` na pilha do AD-6 ou estado local duplicado por tela hospedeira — risco de duplicar gerenciamento de estado mesmo com renderização compartilhada. |

Nenhum destes é um problema de "a ideia é ruim" — todas as 13 ADs
continuam sendo decisões tecnicamente corretas. O problema é que, em pelo
menos 8 delas, **o texto da Rule tem folga suficiente para que duas sessões
de implementação futuras, ambas obedientes ao pé da letra, produzam
artefatos que não interoperam** — seja porque o formato de um dado
compartilhado não é fixado (H10, H12), porque duas ADs se contradizem
diretamente (H2, H11), porque a API pública de um tipo central não é
definida (H4), porque falta um mecanismo nomeado de exclusão mútua (H6), ou
porque a fronteira de responsabilidade entre dois módulos do mesmo nível
não tem uma seta de dependência declarada (H3). Recomendo fechar pelo menos
H2, H3, H6, H11 e H12 (as 5 de maior risco/menor custo de correção) antes de
avançar para `bmad-create-epics-and-stories`, já que todas elas afetam
contratos de dado ou de chamada que múltiplas stories vão depender
simultaneamente.
