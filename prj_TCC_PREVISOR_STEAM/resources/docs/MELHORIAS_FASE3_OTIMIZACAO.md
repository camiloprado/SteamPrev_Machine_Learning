# Melhorias Implementadas — Fase 3: Otimização de ETL, Treinamento e Extensão

**Data**: 24 de agosto de 2026
**Continuação de**: `MELHORIAS_IMPLEMENTADAS.md` (Fase 1 — Engenharia de Dados, Fase 2 — Machine Learning e Sazonalidade)

## Contexto

Com o pipeline de coleta, o treinamento de modelos e o projeto de extensão (aplicação cliente que consome os modelos) já em funcionamento, foi realizado um levantamento sistemático de oportunidades de otimização nas três frentes, priorizando correções de alto impacto e baixo risco dado o cronograma de entrega do TCC. As correções foram validadas comparando três execuções completas do pipeline de treinamento: a versão anterior à refatoração modular (`main`), a versão modular sem as correções desta fase (baseline) e a versão modular com as correções aplicadas.

---

## 1. Engenharia de Dados (ETL/Coleta)

### 1.1 Pool de conexões PostgreSQL duplicado

**Problema**: a classe base `PostgreSQL` inicializa um *connection pool* compartilhado (`_var_poolConnectionPool`), mas cada subclasse especializada (`PostgreSQLSteam`, `PostgreSQLITAD`, `PostgreSQLBDGeral`, `PostgreSQLCheckpoint`) chamava `cls._init_pool()` a partir de si mesma. Em Python, uma atribuição `cls.atributo = valor` dentro de um `classmethod` grava o atributo no `__dict__` da subclasse que efetivamente invocou o método, não no da classe base — resultado: cada subclasse acabava criando seu próprio pool de até 10 conexões, chegando a até 50 conexões simultâneas abertas no banco em vez de 10 compartilhadas.

**Solução**: os pontos de criação, obtenção e devolução de conexão passaram a referenciar explicitamente `PostgreSQL._var_poolConnectionPool` (a classe base), garantindo um único pool real compartilhado entre todas as subclasses.

**Validação**: teste em runtime confirmou `id()` idêntico do pool entre `PostgreSQLSteam` e `PostgreSQLITAD` após a correção, e ausência de pool próprio no `__dict__` de cada subclasse.

### 1.2 Consulta N+1 na integração ITAD

**Problema**: `buscar_itad_id_por_appid` executava um `SELECT` individual por AppID dentro de um laço, chegando a milhares de *round-trips* ao banco por lote (o parâmetro de tamanho de lote do ITAD pode chegar a 80.000 AppIDs).

**Solução**: substituição por uma única consulta em lote (`WHERE appid = ANY(%s)`), preservando o contrato original do método (um valor por AppID de entrada, na mesma ordem, com `None` para os sem mapeamento).

### 1.3 Inserção linha a linha em `steam_generico`

**Problema**: `inserir_dadosSteamGenerico` inseria registros um a um via `cursor.execute`, enquanto o restante do mesmo arquivo já utilizava inserção em lote (`execute_values`/`execute_batch`) para as demais tabelas.

**Solução**: unificação do padrão, substituindo o laço por `execute_batch`.

### 1.4 Consulta redundante e bug latente no orquestrador do pipeline

**Problema**: `Process.execute()` consultava os AppIDs desatualizados de `steam_raw` duas vezes na mesma iteração — uma na Etapa 1 (coleta) e novamente na Etapa 2 (ETL). Além do custo duplicado, havia um risco funcional: como a Etapa 1 já atualiza `ultima_atualizacao` dos AppIDs coletados, uma nova consulta na Etapa 2 podia retornar um conjunto diferente (tipicamente menor) do que o lote que a Etapa 1 efetivamente processou, fazendo a Etapa 2 transformar dados diferentes dos recém-coletados.

**Solução**: a Etapa 2 passou a reaproveitar a lista já obtida na Etapa 1, eliminando a consulta redundante e a inconsistência.

---

## 2. Treinamento de Modelos de Machine Learning

### 2.1 Vazamento de dados *point-in-time* em `preco_catalogo`

**Problema**: a feature `preco_catalogo` era calculada uma única vez a partir do *snapshot* mais recente do preço do jogo (fora do laço de geração de amostras históricas) e reutilizada como valor idêntico em todas as amostras temporais daquele jogo — inclusive amostras referentes a anos atrás. Isso constitui vazamento de informação do futuro para o passado, inflando artificialmente as métricas de treino e teste.

**Solução**: a feature passou a usar o preço vigente no próprio ponto histórico da amostra (`preco_atual_hist`), replicando exatamente a lógica já usada pela API de inferência da extensão no momento da predição — eliminando o vazamento e corrigindo, como efeito colateral, uma inconsistência entre o comportamento de treino e o de produção (*train-serve skew*).

### 2.2 Referência de censura temporal incorreta na rotulagem de horizontes

**Problema**: ao rotular uma amostra como "mantém" quando não havia dados suficientes para confirmar o horizonte (30/60/90 dias), o código usava o timestamp máximo de todo o conjunto de dados como referência. Esse valor, por sua vez, era calculado a partir do último elemento *bruto* (não ordenado) da lista de histórico de cada jogo — se o histórico não vier estritamente ordenado por tempo, esse valor pode subestimar o alcance real dos dados daquele jogo.

**Solução**: a referência passou a ser o último timestamp do histórico já ordenado e validado de cada jogo individualmente, em vez do máximo global do dataset.

**Impacto medido**: comparando a distribuição de rótulos antes e depois da correção, aproximadamente 10 mil amostras por horizonte que antes eram descartadas (rótulo indefinido) passaram a receber um rótulo válido ("mantém"):

| Horizonte | Amostras descartadas antes | Amostras descartadas depois |
|---|---|---|
| 30 dias | 10.473 | 0 |
| 60 dias | 1.614 | 0 |
| 90 dias | 10.759 | 0 |

### 2.3 Acúmulo de artefatos `.joblib` em disco

**Problema**: cada execução de treino grava uma versão com timestamp de cada modelo, sem qualquer rotina de limpeza, e sem compressão — o diretório de modelos acumulava mais de 300 arquivos e 13 GB.

**Solução**: adição de `compress=3` em todas as chamadas `joblib.dump` e implementação de uma rotina de retenção que mantém apenas as 3 versões mais recentes por combinação de algoritmo e horizonte (preservando sempre o alias `_latest`).

**Impacto medido**: o modelo de classificação RandomForest do horizonte de 30 dias caiu de 417 MB (sem compressão) para 162 MB (com `compress=3`) — redução de aproximadamente 61%.

### 2.4 Rastreabilidade experimental

**Problema**: o `manifest.json` com as métricas de cada execução é sobrescrito a cada novo treino, impossibilitando comparar a evolução das métricas ao longo do desenvolvimento.

**Solução**: introdução de `manifest_history.jsonl`, um registro *append-only* (uma linha JSON por execução) mantido em paralelo ao `manifest.json`.

### 2.5 Validação experimental das correções

As três correções acima foram validadas executando o pipeline de treinamento completo três vezes, sobre a mesma base de dados, comparando os resultados:

| Métrica | `main` (arquitetura anterior) | `homolog` sem as correções | `homolog` com as correções |
|---|---|---|---|
| F1-macro — Classificação 30d | 0,6208 | 0,6400 | 0,6180 |
| F1-macro — Classificação 60d | 0,5731 | 0,5965 | 0,5761 |
| F1-macro — Classificação 90d | 0,5039 | 0,5205 | 0,5184 |
| RMSE — Regressão dias 30d | 5,90 | 5,90 | 5,88 |
| RMSE — Regressão desconto 30d (%) | — | 8,98 | 8,91 |
| RMSE — Regressão desconto 60d (%) | — | 9,49 | 9,45 |
| RMSE — Regressão desconto 90d (%) | — | 10,29 | 10,26 |

A leve redução no F1-macro de classificação entre o baseline e a versão corrigida é esperada e desejável: o baseline apresentava métricas infladas pelo vazamento de dados descrito em 2.1. A regressão de desconto, por sua vez, apresentou melhora consistente nos três horizontes após a correção — resultado coerente, já que `preco_catalogo` também é utilizada no cálculo do preço estimado de desconto. O regressor de dias praticamente não se alterou, pois sua lógica de extração de alvo não foi modificada por nenhuma das correções. A versão `main`, arquiteturalmente anterior à modularização do pipeline (Single Responsibility), não possui o regressor de desconto por horizonte, introduzido apenas na fase de refatoração.

---

## 3. Projeto de Extensão (Consumo dos Modelos)

O projeto de extensão (repositório separado, responsável pela API de inferência, dashboard, bot e extensão de navegador) estava com um checkout local desatualizado em relação ao repositório remoto, contendo além disso alterações não commitadas que, sem que fosse percebido, revertiam correções já publicadas. A reconciliação trouxe de volta:

- Configuração de CORS mais restritiva (`allow_credentials=False`), evitando combinar uma política de origem permissiva com o uso de credenciais.
- Execução das chamadas de carregamento e inferência dos modelos em thread separada (`asyncio.to_thread`), eliminando o bloqueio do laço de eventos da API sob requisições concorrentes.
- Sinalização ao usuário, via campo `fonte` no histórico de preços, sempre que a API do ITAD cai no modo simulado (mock) — cobrindo não apenas limite de requisições, mas também chave de API ausente e falhas de rede.
- Cópia do diretório `scripts/` no `Dockerfile` da API, necessária para o download automático dos modelos publicados, sem a qual o deploy em produção falhava silenciosamente.

Adicionalmente, o `manifest.json` consumido pela API de predição passou a ser mantido em cache em memória (invalidado por data de modificação do arquivo), eliminando a leitura e o parse do arquivo em disco a cada requisição de predição.

---

## Resumo

| Frente | Correções aplicadas | Tipo de ganho |
|---|---|---|
| ETL/Coleta | Pool de conexões, N+1 no ITAD, insert em lote, consulta redundante | Desempenho e correção de bug latente |
| Treinamento | Vazamento de dados, censura temporal, compressão/retenção, rastreabilidade | Confiabilidade metodológica e uso de disco |
| Extensão | Reconciliação com correções de CORS, concorrência, cache de modelos | Segurança, robustez e desempenho |

Todas as correções foram validadas por execução real — consultas testadas contra o banco de dados de produção, e as correções de treinamento validadas por comparação de três execuções completas do pipeline.
