# Review — Versões e Checagem Contra a Realidade

Escopo desta review: verificar que toda decisão de versão/tecnologia no `ARCHITECTURE-SPINE.md` foi checada contra a realidade (crates.io ao vivo, `Cargo.lock`/`Cargo.toml` real do crate, `PROJECT_MEMORY.md`, metadata real do FIFA 16), em vez de apenas afirmada de memória de treinamento. Não repete os achados estruturais já cobertos em `review-rubric.md`; foca especificamente em versões, existência/adequação de tecnologia, e alegações sobre comportamento de API de terceiros.

## Veredito geral

Todas as versões comprometidas na tabela Stack foram de fato verificadas — as quatro dependências novas (`serde`, `serde_json`, `uuid`, `dirs`) têm nota explícita de verificação com data, e os números batem com o que `crates.io`/`docs.rs` reportam hoje; as cinco dependências `[ADOPTED]` (`hudhook`, `imgui`, `windows`, `memchr`, `tracing`/`tracing-subscriber`/`tracing-appender`) batem exatamente com o `Cargo.lock` real do crate `fifa_overlay`, não são suposição. Não encontrei nenhuma alegação sobre comportamento de API de terceiros (hudhook/imgui/windows-rs) que dependa de memória de treinamento não confirmada — as únicas afirmações técnicas concretas sobre essas APIs (ex: `ImguiRenderLoop::render`, `ReadProcessMemory`/`WriteProcessMemory`, a convenção `.get(a..b)`) são sobre código **já existente e lido diretamente** no crate, não sobre comportamento não verificado de uma lib externa. A combinação de features `uuid` v4+serde é real e documentada. Único ponto genuinamente fraco: o `[ASSUMPTION]` de `GJUr.startdate`/`mPrV.clubteamid` é tratado com o rigor correto (marcado como não validado), mas a spine poderia ter checado — e não checou explicitamente — se esses dois campos *existem* no metadata real antes de comprometê-los na Rule do AD-11; eu fiz essa checagem agora e ambos existem, então não há erro de fato, só uma checagem que ficou faltando registrar no processo.

## 1. Tabela Stack — versões novas com nota de verificação

| Crate | Versão no spine | Nota do spine | Confirmado ao vivo (crates.io/docs.rs) |
| --- | --- | --- | --- |
| `serde` (derive) | 1.0 | "verificado 2026-09-22, atual 1.0.229" | ✅ 1.0.229 é de fato a versão mais recente listada em docs.rs (publicada 2026-07-18), não yanked |
| `serde_json` | 1.0 | "verificado 2026-09-22, atual 1.0.151" | ✅ 1.0.151 é a mais recente (publicada 2026-07-20), não yanked |
| `uuid` (v4, serde) | 1.26 | "verificado 2026-09-22, atual 1.26.1" | ✅ 1.26.1 é a mais recente (publicada 2026-09-10), não yanked |
| `dirs` | 7.0 | "verificado 2026-09-22, atual 7.0.0" | ✅ 7.0.0 é a mais recente (publicada 2026-09-05), não yanked |

As quatro linhas cumprem exatamente o critério pedido: citam a data da verificação e a versão atual real, e as duas batem. Isso está registrado de forma consistente também no `.memlog.md` (linha 36), o que indica que a verificação aconteceu durante a sessão de elicitação, não foi adicionada post-hoc sem lastro.

**Nota lateral (não é erro, é observação de rastreabilidade):** nenhuma dessas quatro dependências aparece ainda no `Cargo.lock` real (`fifa_overlay/Cargo.lock` não tem `serde`, `serde_json`, `uuid` nem `dirs`) — confirmei isso rodando `Select-String` no lockfile. Isso é esperado e correto: são dependências **novas**, ainda não adicionadas ao `Cargo.toml`, então a spine está certa em não afirmar um "resolvido X.Y.Z" para elas (diferente das `[ADOPTED]`, que já têm resolução real no lockfile).

## 2. Versões `[ADOPTED]` — checadas contra o Cargo.lock real, não assumidas

Comparei cada linha da tabela Stack marcada `[ADOPTED]` contra `fifa_overlay/Cargo.toml` e `fifa_overlay/Cargo.lock` reais:

| Crate | Spine diz | `Cargo.toml` real | `Cargo.lock` resolvido real | Bate? |
| --- | --- | --- | --- | --- |
| Rust edition | 2021 | `edition = "2021"` | — | ✅ |
| hudhook (dx11) | 0.9, resolvido 0.9.3 | `hudhook = { version = "0.9", features = ["dx11"] }` | `version = "0.9.3"` | ✅ |
| imgui | 0.12, resolvido 0.12.0 | `imgui = "0.12"` | `version = "0.12.0"` | ✅ |
| windows | 0.62, resolvido 0.62.2 | `version = "0.62"` (features Win32_Foundation/Memory/Threading/Diagnostics_Debug/ProcessStatus) | `version = "0.62.2"` | ✅ |
| memchr | 2.7, resolvido 2.8.3 | `memchr = "2.7"` | `version = "2.8.3"` | ✅ |
| tracing/tracing-subscriber/tracing-appender | 0.1/0.3/0.2 | mesmos requisitos no `Cargo.toml` | `0.1.44`/`0.3.23`/`0.2.5` | ✅ |

Todas as cinco linhas `[ADOPTED]` são fiéis ao lockfile real, não são suposição — a distinção "declarado no Cargo.toml" vs. "resolvido no Cargo.lock" está corretamente feita para hudhook/imgui/windows/memchr (a spine cita ambos os números).

**Finding — low, formatação/inconsistência, não erro de fato:** a linha de `tracing`/`tracing-subscriber`/`tracing-appender` não cita a versão "resolvida" (0.1.44/0.3.23/0.2.5) como as outras quatro linhas `[ADOPTED]` fazem — só repete a versão declarada no `Cargo.toml` (0.1/0.3/0.2). Os números resolvidos corretos **existem** no `.memlog.md` (linha 10), então a informação foi capturada durante a pesquisa, só não foi transcrita para a tabela final do spine com o mesmo padrão "resolvido X.Y.Z" usado nas outras quatro linhas. Não afeta a validade da decisão, é só uma inconsistência de apresentação dentro do próprio spine.

## 3. Combinação de features `uuid` v4 + serde

Confirmei ao vivo em `docs.rs/uuid/1.26.1` que:
- `v4` é uma feature real e documentada ("Version 4 UUIDs with random data").
- `serde` é uma feature real e documentada ("adds the ability to serialize and deserialize a UUID using serde"), listada na seção "Other features", claramente independente/combinável com as features de versão de UUID.
- A própria página de dependências do crate (docs.rs) lista `serde_core` como dependência opcional ativada pela feature `serde` — confirma que a combinação `features = ["v4", "serde"]` compila e é um padrão usado e documentado pelo próprio mantenedor do crate, não uma combinação hipotética.

Não é uma alegação arriscada — é o uso mais comum e recomendado do crate `uuid` em qualquer projeto que precise serializar UUIDs gerados aleatoriamente. Dupla checagem passa sem ressalva.

## 4. Afirmações técnicas fora da tabela Stack sobre comportamento de API de terceiros

Vasculhei o corpo do spine (ADs, Consistency Conventions, Structural Seed, árvore de arquivos) procurando qualquer alegação sobre **como uma API de terceiro se comporta** que não tivesse sido conferida contra o código real ou contra `PROJECT_MEMORY.md`. Resultado:

- **`ImguiRenderLoop::render` "passa a despachar para `scout::render_active_screen(...)`"** (árvore de arquivos, comentário em `lib.rs`) — não é uma alegação sobre comportamento do hudhook/imgui em si, é uma descrição do que o *próprio código do projeto* vai fazer dentro do método `render()` que hudhook já invoca. `hudhook::ImguiRenderLoop` e o método `render()` existem de fato — confirmei em `lib.rs:19` (`use hudhook::ImguiRenderLoop;`) e `lib.rs:355-357` (`impl ImguiRenderLoop for FifaOverlay { fn render(&mut self, ui: &mut imgui::Ui) {`). Não é uma suposição sobre a lib, é leitura direta do código já existente.
- **`ReadProcessMemory`/`WriteProcessMemory`** (Consistency Conventions, linha 135; AD-2) — funções reais do Win32 API, já em uso ativo em `memscan.rs:35` (`use windows::Win32::System::Diagnostics::Debug::{ReadProcessMemory, WriteProcessMemory};`). Não é uma alegação nova, é reafirmação de padrão já implementado e testado (ver `PROJECT_MEMORY.md` linhas 945-963, sessão 5, onde a troca de deref de ponteiro cru para `ReadProcessMemory` protegido foi implementada e validada empiricamente contra crash real).
- **`.get(a..b)` em vez de `&slice[a..b]`** ("bug histórico documentado") — confirmei que esse bug e a correção estão de fato documentados em `PROJECT_MEMORY.md:1076-1082` ("Bug de segurança de memória... `&bytes[a..b]`... pode gerar `panic!`..."). Não é uma alegação genérica de boas práticas Rust vinda de memória de treinamento — é um bug real do próprio projeto, com causa raiz e correção documentadas.
- **AsyncTask/`Arc<Mutex<TaskState<T>>>` + `Arc<AtomicBool>` "já duplicado 3× no código existente"** (AD-4) — confirmei em `lib.rs`: três pares distintos (`ScanState`/`scan_in_progress`, `PointerScanState`/`pointer_scan_in_progress`, `ValueScanState`/`value_scan_in_progress`), cada um com `Arc<Mutex<...>>` + `Arc<AtomicBool>` e `spawn_*_thread` correspondente. Alegação verificada linha a linha, não é estimativa.
- **"scan completo de `CZUM` roda em thread separada (~17s, sem travar o render)"** (Deferred, último item) — confirmei em `PROJECT_MEMORY.md:965-970` ("scan em background completa em ~17s... Jogo permaneceu 100% estável"). Número real de uma sessão de teste documentada, não uma estimativa genérica.
- **`GJUr.startdate` / `mPrV.clubteamid` / `mPrV.firstname`/`surname`** (AD-11) — estes são os únicos campos citados no spine com risco genuíno de vir de memória de treinamento sem confirmação, porque a spine explicitamente admite que `GJUr.startdate` "ainda não foi lido/validado" e marca isso com `[ASSUMPTION]`. Fiz a checagem que faltava: consultei o metadata real do FIFA 16 instalado (`D:\Program Files\FIFA 16\data\db\fifa_ng_db-meta.xml`) e confirmei que os três campos **existem de fato**: `career_calendar` (shortname `GJUr`) tem o campo `startdate` (shortname `vHhZ`, linha 2229) e `career_users` (shortname `mPrV`) tem `firstname`, `surname` e `clubteamid` (shortname `NTyS`, linha 1022). Ou seja, a spine não inventou nomes de campo — eles existem no schema real —, mas a *estabilidade ao longo de múltiplas sessões* de `startdate` (a parte que importa para o pseudo-ID do AD-11) é de fato não testada, exatamente como o `[ASSUMPTION]` e o item em Deferred admitem. **Nenhum erro de fato aqui, mas vale registrar que essa checagem de existência de campo eu tive que fazer agora — não havia evidência no spine ou no `.memlog.md` de que os nomes de campo em si (`startdate`, `clubteamid`) tivessem sido confirmados contra o XML real antes de comprometer a Rule.** Recomendo, se possível, adicionar uma nota ao AD-11 ou ao item de Deferred citando que os nomes de campo foram confirmados no `fifa_ng_db-meta.xml`, deixando explícito que só a *estabilidade temporal* do valor é o que falta validar — hoje o texto mistura as duas coisas sob um único `[ASSUMPTION]`, o que é levemente impreciso (a existência do campo não é suposição, é fato já verificável; só o comportamento dele ao longo do tempo é).

Não encontrei nenhuma alegação sobre uma feature específica do crate `windows` (ex: nomes de submódulos Win32 além dos já usados em `memscan.rs`), nem sobre comportamento interno de `hudhook`/`imgui` (ex: threading model, ciclo de vida de frame) que não estivesse ancorada em código já existente e lido. O spine é disciplinado nesse aspecto — quando introduz algo genuinamente novo e não verificado (como `GJUr.startdate` estável), ele marca explicitamente com `[ASSUMPTION]` e lista como item de validação em Deferred, em vez de comprometer silenciosamente.

## Resumo dos findings

- **low** — Inconsistência de formatação na tabela Stack: a linha `tracing`/`tracing-subscriber`/`tracing-appender` não cita as versões resolvidas (0.1.44/0.3.23/0.2.5, já presentes no `.memlog.md`) no mesmo padrão "resolvido X.Y.Z" usado por hudhook/imgui/windows/memchr. Sem impacto técnico, só falta de paridade de apresentação dentro do próprio documento.
- **low** — AD-11 mistura sob um único `[ASSUMPTION]` duas coisas de natureza diferente: (a) a *existência* dos campos `GJUr.startdate`/`mPrV.clubteamid` no schema do FIFA 16 — que eu confirmei agora contra o `fifa_ng_db-meta.xml` real e são fatos, não suposição — e (b) a *estabilidade temporal* de `startdate` ao longo de múltiplas sessões da mesma carreira, que de fato não foi testada e é a parte genuinamente incerta. Sugestão: separar as duas no texto do AD-11, deixando claro que o campo existe (fato verificado) e só o comportamento dele ao longo do tempo é a assunção pendente.

Nenhum finding de severidade `high`/`critical` encontrado nesta frente. Todas as versões de biblioteca comprometidas na tabela Stack foram genuinamente verificadas contra crates.io/docs.rs com data registrada, todas as versões `[ADOPTED]` batem com o `Cargo.lock` real do projeto, e nenhuma alegação de comportamento de API de terceiro no corpo do spine depende de memória de treinamento não confirmada — as poucas alegações técnicas fora da tabela Stack são sobre código já existente e lido diretamente pelo autor da spine, ou sobre resultados empíricos já documentados em `PROJECT_MEMORY.md`.
