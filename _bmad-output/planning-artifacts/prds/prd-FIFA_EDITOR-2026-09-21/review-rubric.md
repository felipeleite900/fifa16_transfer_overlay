# PRD Quality Review — Central de Scout — FIFA 16 Companion

## Overall verdict

Para um PRD hobby de dev único, este documento é incomumente sólido: decisões são de fato decisões (custo real de orçamento, sem reembolso, sem limite de slots — cada uma com o trade-off nomeado), o Não-Objetivos faz trabalho de verdade, e quase todo FR tem consequência testável em vez de adjetivo vago. As referências técnicas ao `PROJECT_MEMORY.md` (hook de `Present()`, escrita validada de `transferbudget`, limitação de escrita per-player, tabelas `CZUM`/`GJUr`/`RrqT`/`Crbb`/`zlrC`/`apoo`) foram conferidas contra o histórico do projeto e estão corretas. O risco real está em disciplina inconsistente de itens em aberto: a fórmula de **Qualidade** — o valor calculado mais central de toda a feature — e a fórmula de similaridade do **Jogador de Referência** não foram marcadas como `[ASSUMPTION]`/Questão em Aberto, ao contrário do Fit Posicional, que recebeu exatamente esse tratamento no mesmo nível de detalhe. Corrigido isso, o documento está pronto para alimentar `bmad-create-epics-and-stories` e `bmad-architecture`.

## Decision-readiness — adequate

O PRD toma posição em vez de amaciar: FR-2 nomeia explicitamente a troca feita ("[ASSUMPTION] Não há limite de slots simultâneos... simplicidade sobre realismo, revisitável em v2" — §4.2), o custo do olheiro debita orçamento real do clube (uma escolha deliberada de peso estratégico, não um "cheat sem custo", ver §2.1), e o `[NOTE FOR PM]` em §6.2 está numa tensão real (o "núcleo de olheiros detalhistas" foi validado como valioso na elicitação mas adiado), não num checkpoint seguro. As Questões em Aberto (§8) são de fato abertas — nenhuma tem a resposta na frase seguinte.

Um fork de decisão relevante fica sem tratamento: o PRD declara em §5 que a Central de Scout "não substitui nem se integra com `career_scouts` (`zlrC`)/`career_scoutmission` (`apoo`) nativos do save — é um sistema paralelo e desacoplado", mas nunca explicita por que essa alternativa (usar as tabelas nativas já existentes no schema do save como armazenamento, em vez de um arquivo de estado próprio do Companion) foi descartada. Isso importa porque a persistência de estado entre sessões é literalmente a Questão em Aberto #1 — um leitor atento perguntaria "por que não gravar as Missões nessas tabelas que já existem no save, já que elas estão vazias mesmo?" e o PRD não antecipa nem rejeita essa objeção.

### Findings
- **high** Alternativa de armazenamento nativo (`zlrC`/`apoo`) não é confrontada (§5, §8 Q1) — a decisão de manter estado 100% no Companion em vez de usar as tabelas nativas de scout já existentes no save (hoje vazias) não é justificada nem descartada explicitamente, apesar de a persistência ser a Questão em Aberto #1. *Fix:* adicionar uma frase em §8-Q1 ou um `[NOTE FOR PM]` explicando por que o caminho "arquivo de estado do Companion" foi preferido a "escrever a estrutura de Missão nas tabelas nativas do save" (ex: risco de escrita estruturada complexa vs. só `transferbudget` já validado).

## Substance over theater — strong

Nenhuma persona-teatro: existe efetivamente uma persona (Felipe), coerente com o formato hobby/solo-operador. A Visão (§1) é específica ao produto — cita a superficialidade real do scouting nativo do FIFA 16, o fato de a EA ter *removido* até esse pouco em versões seguintes, e a referência concreta ao padrão de profundidade do Football Manager — não é um parágrafo genérico que serviria para qualquer PRD da categoria. Não há seção de NFR copiada em boilerplate ("deve ser escalável/seguro"); o único risco de performance (leitura contínua de memória via `CZUM`/`RrqT`) é tratado honestamente como Questão em Aberto #5, não varrido para debaixo do tapete.

## Strategic coherence — strong

A tese é explícita: transformar "a janela morta de esperar a carreira avançar" em "um loop de descoberta ativo e estratégico" (§1). A priorização de features segue essa tese — Fit Posicional e Jogador de Referência (os filtros que a EA nunca ofereceu) são tratados como núcleo do MVP, não deixados para depois — em vez de seguir "o que é mais fácil primeiro". SM-1 mede comportamento real (preferir a Central de Scout à busca nativa), não uma métrica de vaidade tipo contagem de sessões, e SM-C1 nomeia explicitamente uma contra-métrica (não otimizar por número de Missões criadas). O parágrafo final de §7 calibra corretamente a stakes: "o critério real e suficiente é: eu volto a usar isso... em vez de abandonar depois de testar uma vez."

## Done-ness clarity — adequate

Esta é a dimensão mais forte do documento em volume — quase todo FR tem consequência testável e concreta em vez de "funciona bem"/"performance razoável": FR-1 especifica comportamento em fullscreen exclusivo e estado vazio sem carreira carregada; FR-3 especifica bloqueio por saldo insuficiente e re-leitura pós-escrita; FR-9/FR-10 especificam exatamente o que Qualidade baixa vs. alta revela (faixas vs. valores exatos, subconjunto vs. perfil completo, radar não inventa eixos faltantes). Isso é o padrão certo para uma dimensão que a rubric pede para tratar sem complacência.

Dois buracos reais quebram essa consistência. A **fórmula de Qualidade** (`Tier do Olheiro × Especialização × Modo de Busca × amplitude geográfica`) é citada em FR-4, FR-5, FR-9 e FR-10 como o mecanismo central de todo o valor da feature — mas, ao contrário do Fit Posicional (FR-6), que recebeu corretamente um `[ASSUMPTION]` explícito adiando a fórmula para a arquitetura, a fórmula de Qualidade nunca é marcada como assumida nem aparece em Questões em Aberto (§8 só cobre custo/tempo em Q3, não a Qualidade em si). Um engenheiro lendo o PRD não tem como saber se isso é "trivial, resolver na hora" ou "decisão de design pendente" — é exatamente o tipo de ambiguidade que esta dimensão existe para pegar. O mesmo padrão se repete em FR-7: o "percentual/indicador de similaridade" com o Jogador de Referência nunca tem sua fórmula mencionada nem sinalizada como pendente.

### Findings
- **high** Fórmula de Qualidade sem tratamento de pendência (§4.3 FR-4/FR-5, §4.4 FR-9/FR-10) — o cálculo mais central da feature (Tier × Especialização × Modo de Busca × amplitude geográfica) nunca recebe `[ASSUMPTION]` nem entrada em Questões em Aberto, ao contrário do tratamento dado ao Fit Posicional (FR-6) para o mesmo tipo de lacuna. *Fix:* adicionar uma Questão em Aberto (ou estender a Q3 de §8) cobrindo explicitamente a fórmula de Qualidade, não só custo/tempo.
- **medium** Fórmula de similaridade do Jogador de Referência não definida nem sinalizada (§4.3 FR-7) — "percentual/indicador de similaridade" não tem fórmula nem é marcado como pendente, mesma lacuna do Fit Posicional mas sem o mesmo cuidado de rotulagem. *Fix:* adicionar `[ASSUMPTION]`/Questão em Aberto equivalente à de FR-6.

## Scope honesty — strong

O Não-Objetivos (§5) faz trabalho real, não é lista de enchimento: nomeia explicitamente o que não é feito e por quê (limitação de escrita per-player já documentada, sistema paralelo e desacoplado das tabelas nativas, sem acúmulo de conhecimento estilo FM, sem suporte a outras versões). Seis `[ASSUMPTION]`s inline estão indexados em §9 (roundtrip quase perfeito — ver Notas Mecânicas). A densidade de itens em aberto (5 Questões + 6 Assunções + 1 `[NOTE FOR PM]`) é proporcional às stakes de um PRD hobby, como a rubric permite. O único ponto fraco é o espelho da lacuna já registrada em Done-ness: a ausência de marcação nas fórmulas de Qualidade e similaridade quebra a mesma disciplina que o PRD demonstrou em outros lugares (Fit Posicional, slots de Olheiro, granularidade do Sonar).

### Findings
- **low** Disciplina de marcação inconsistente entre fórmulas pendentes (ver findings em Done-ness clarity) — mesma causa raiz, apenas reforçando que o padrão de tagging do documento (forte em geral) tem essas duas exceções notáveis.

## Downstream usability — adequate

O PRD se declara "standalone por enquanto", mas explicitamente destinado a alimentar `bmad-create-epics-and-stories` e `bmad-architecture` (§0) — então esta dimensão pesa mais do que o padrão "standalone, mais leve" da rubric. Estruturalmente está bem pronto para extração: IDs de FR (1–11), UJ (1–3) e SM (1, 2, C1) são contíguos e sem duplicação; referências cruzadas (FR-4 → FR-6/FR-7, notas de §4.3 → §8) resolvem corretamente; cada seção de Feature (Descrição/FRs/Consequências/Fora de Escopo) é razoavelmente autocontida.

Um termo do Glossário é cunhado e nunca reutilizado: **"Orçamento de Scouting"** (§3) é definido com uma tag `[ASSUMPTION]` própria, mas o resto do documento (FR-2, FR-3, §2.1) sempre diz "orçamento do clube"/"orçamento real do clube"/`transferbudget`, nunca o termo do Glossário. Para um documento cujo §0 diz "o vocabulário do Glossário é vinculante — features e FRs usam esses termos literalmente", essa é uma inconsistência pequena mas real, que pode confundir uma passada futura de arquitetura procurando pelo termo canônico.

### Findings
- **low** Termo de Glossário não reutilizado (§3 "Orçamento de Scouting" vs. uso real em §2.1/§4.2/§4.3) — o termo vinculante nunca aparece fora da própria definição. *Fix:* usar "Orçamento de Scouting" nas FRs relevantes (FR-2, FR-3) ou remover o termo do Glossário e manter só a nota de que é o mesmo `transferbudget`.

## Shape fit — strong

O formato está bem calibrado para hobby/solo: uma persona (o próprio Felipe), UJs com protagonista nomeado e contexto real (não UJs floating), sem excesso de formalismo tipo múltiplas personas fictícias. A extensão do documento (Glossário, Índice de Suposições, JTBD) se justifica pelo propósito declarado de alimentar as próximas sessões de arquitetura/épicos — não é enchimento de template. As referências brownfield foram verificadas contra `PROJECT_MEMORY.md` e batem: hook de `Present()` (sessão 5), escrita validada de `transferbudget` (sessão 4/5), limitação não resolvida de escrita per-player (sessões 2–5), tabelas `CZUM`/`GJUr`/`Crbb`/`zlrC`/`apoo` todas citadas corretamente. §7 reconhece explicitamente a natureza hobby ao dispensar métricas de produto formais — autoconsciência correta de escopo.

## Mechanical notes

- **Assumptions Index roundtrip quebrado em 1 ponto**: a entrada `[§2.3, UJ-1]` em §9 ("Fluxo assume que o usuário sempre finaliza a contratação real do jogador manualmente na tela nativa...") não tem tag `[ASSUMPTION]` correspondente inline em §2.3/UJ-1 — o texto da UJ apenas afirma isso como fato na "Resolução", sem marcação. Como esse mesmo ponto já está coberto como Não-Objetivo explícito em §5, considerar remover a entrada do Índice (redundante) ou adicionar a tag inline em UJ-1 para consistência.
- **Glossary drift**: ver finding de Downstream usability acima ("Orçamento de Scouting" cunhado mas não reutilizado). Fora isso, os termos do Glossário (Olheiro, Especialização, Tier, Missão, Modo de Busca, Filtro, Fit Posicional, Jogador de Referência, Relatório, Qualidade, Sonar de Cobertura, Radar de Atributos) são usados de forma consistente nas FRs, incluindo abreviações aceitáveis (`Missão` por `Missão de Scouting`, `Relatório` por `Relatório de Scouting`).
- **ID continuity**: limpo — FR-1 a FR-11 contíguos sem lacunas, UJ-1 a UJ-3 contíguos, SM-1/SM-2/SM-C1 sem duplicação.
- **Formato `[NON-GOAL for MVP]`**: o PRD usa uma seção prosa de "Não-Objetivos (Explícitos)" (§5) em vez do tag inline sugerido pela rubric — cumpre a mesma função com a mesma força, apenas formato diferente. Cosmético, sem ação necessária.
- **UJ protagonist naming**: as três UJs (§2.3) nomeiam Felipe como protagonista com contexto inline (orçamento apertado, carreira avançada, início de carreira com pouco dinheiro) — sem UJs floating.
