# Software Design Document (SDD)
## Previsor Steam — TCC de Ciência da Computação

**Autor:** Camilo Prado  
**Curso:** Ciência da Computação  
**Versão:** 2.0  
**Data:** Maio de 2026  

---

## 1. Visão Geral

### 1.1 Propósito

O **Previsor Steam** é um sistema automatizado de coleta, processamento e análise de dados do ecossistema de jogos da plataforma Steam. O objetivo central é predizer padrões de desconto e estimar o sucesso comercial de jogos utilizando modelos de Machine Learning treinados sobre dados históricos de mais de 270.000 títulos.

### 1.2 Escopo

O sistema realiza, de forma autônoma e contínua:
- Coleta de dados via Steam API, SteamSpy e IsThereAnyDeal (ITAD)
- Armazenamento em PostgreSQL local (Docker)
- Processamento ETL com limpeza e normalização de dados
- Treinamento de modelos preditivos (classificação de direção de preço + regressão de dias até desconto)
- Persistência e comparação de modelos treinados

### 1.3 Problema de Negócio

| Problema | Solução Proposta |
|---|---|
| Prever o melhor momento para comprar um jogo com desconto | Regressão: dias estimados até o próximo desconto |
| Classificar a tendência de preço de um jogo | Classificação: `sobe`, `mantem`, `cai` |
| Identificar características que impactam o sucesso | Feature importance dos modelos treinados |

---

## 2. Arquitetura do Sistema

### 2.1 Visão Arquitetural

```
┌─────────────────────────────────────────────────────────────┐
│                        bot.py (entry point)                 │
│   Initialization → Loop → Process → End                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────▼─────────────────┐
         │         Process.execute()         │
         │  (pipeline completo por iteração) │
         └──┬──────────┬──────────┬──────────┘
            │          │          │
     Etapa 1-2    Etapa 3-4   Etapa 5
      Steam       ITAD         ML
        │           │           │
   ┌────▼────┐ ┌────▼────┐ ┌───▼────────┐
   │steam_raw│ │itad_raw │ │treinar_    │
   │steam_   │ │steam_   │ │modelos.py  │
   │unificado│ │itad_map │ │resources/  │
   └─────────┘ └─────────┘ │models/     │
                            └────────────┘
```

### 2.2 Padrão de Design

O sistema segue o padrão **Bot Framework com fila de tarefas única**:

- `Initialization` — bootstrap (Docker, índice de apps)
- `Loop` — consome a fila enquanto houver itens
- `Process` — executa o pipeline completo por iteração
- `End` — encerramento seguro

A fila contém **exatamente 1 item** por sessão. Isso garante que o pipeline rode uma vez por execução do bot, sem paralelismo desnecessário.

---

## 3. Módulos e Componentes

### 3.1 `classes/framework/`

| Arquivo | Classe | Responsabilidade |
|---|---|---|
| `AllSettings.py` | `Settings` | Carrega `.env`, configura logging, inicia Docker |
| `Initialization.py` | `Initialization` | Ponto de entrada da fase de boot — chama `InitApplication` |
| `InitApplication.py` | `InitApplication` | Verifica Docker, atualiza índice de apps, cria fila |
| `Loop.py` | `Loop` | Executa iterações enquanto fila não estiver vazia, com retry |
| `Process.py` | `Process` | Pipeline completo: coleta → ETL → ITAD → treinamento |
| `End.py` / `Close.py` | `End`, `Close` | Encerramento seguro da aplicação |

#### Fluxo de Retry (`Loop`)
```
for tentativa in range(max_tentativas):
    try:
        Process.execute()
        fila.pop()
    except Exception:
        if última tentativa: raise
        InitApplication.execute(firstRun=False)  # reinicia sem recriar fila
```

### 3.2 `classes/api/`

| Arquivo | Classe | API | Dados Coletados |
|---|---|---|---|
| `steam_api.py` | `SteamClient` | Steam Store API | Detalhes do jogo (JSONB), reviews |
| `steamspy_api.py` | `SteamSpyClient` | SteamSpy API | Lista de 280k+ AppIDs com metadados básicos |
| `itad_api.py` | `ITADClient` | IsThereAnyDeal API | Mapeamento Steam↔ITAD, histórico de preços |
| `local_steam.py` | `LocalClient` | Cache local | Fallback para `steam_applist.json` |

#### Estratégia de Coleta Steam
- **Batch assíncrono** via `aiohttp` com concorrência configurável
- **Adaptive batch sizing**: aumenta/reduz tamanho do batch conforme taxa de sucesso
- **Retry com backoff**: 3 tentativas, espera de 240s em caso de HTTP 429
- **Checkpoint**: retomada do índice exato em caso de interrupção

### 3.3 `classes/data/`

| Arquivo | Responsabilidade |
|---|---|
| `previsor.py` | Orquestra a alimentação dos bancos Steam e ITAD |
| `repositories/postgre_steam.py` | CRUD em `steam_raw` e `steam_generico` |
| `repositories/postgre_itad.py` | CRUD em `itad_raw` e `steam_itad_mapping` |
| `repositories/postgre_generico.py` | Pool de conexões compartilhado, operações genéricas |
| `repositories/postgre_bdgeral.py` | Tabela `steam_geral` (base unificada) |
| `repositories/postgre_checkpoint.py` | Leitura/escrita de checkpoints por PC e tipo |
| `repositories/postgre_criar_tabela.py` | DDL e criação de tabelas |

### 3.4 `classes/limpeza/`

| Arquivo | Domínio de Limpeza |
|---|---|
| `ProcessadorETL.py` | Orquestrador: `steam_raw` → `steam_unificado` |
| `limpeza.py` | Utilitários genéricos (`Limpar.normalizar_texto`, extração segura) |
| `limpeza_categoria.py` | Normalização de categorias (multi-label) |
| `limpeza_genero.py` | Normalização de gêneros |
| `limpeza_linguagens.py` | Normalização de idiomas (189 idiomas mapeados) |
| `limpeza_data_lancamento.py` | Parse de datas em múltiplos formatos |
| `limpeza_preco.py` | Conversão de preço (R$ string → float) |
| `limpeza_metacritic.py` | Normalização do score Metacritic |
| `limpeza_desenvolvedor.py` / `limpeza_distribuidores.py` | Normalização de créditos |
| `limpeza_nome.py` / `limpeza_idade.py` | Nome e classificação etária |

### 3.5 `classes/treinamento/`

| Arquivo | Classe | Responsabilidade |
|---|---|---|
| `ProcessadorTreinamento.py` | `ProcessadorTreinamento` | Ponto de entrada chamado pelo `Process` |
| `treinar_modelos.py` | `Treinar_Modelos` | Implementação dos 6 modelos + persistência |
| `normalizar_modelos.py` | `NormalizarModelos` | Carga de dados, splits treino/teste, normalização |

### 3.6 `classes/utils/`

| Arquivo | Responsabilidade |
|---|---|
| `GetTask.py` | Atualiza índice de apps e insere 1 tarefa na fila |

---

## 4. Banco de Dados

### 4.1 Tabelas Principais

| Tabela | Tamanho Aprox. | Descrição |
|---|---|---|
| `steam_generico` | 25 MB / 276k registros | Índice operacional: appid, nome, timestamps |
| `steam_raw` | ~1.2 GB / 276k registros | Dados brutos JSONB (detalhes + reviews da Steam API) |
| `steam_unificado` | ~1.6 GB / 229k registros | Dados ETL estruturados — fonte principal de ML |
| `itad_raw` | ~178 MB / 227k registros | Histórico de preços ITAD (JSONB) |
| `steam_itad_mapping` | ~56 MB / 227k registros | Mapeamento AppID Steam ↔ slug ITAD |
| `processing_checkpoint` | < 1 MB | Checkpoint de índice por (pc_id, tipo) |

### 4.2 Schema Simplificado — `steam_unificado`

```sql
CREATE TABLE steam_unificado (
    appid               INTEGER PRIMARY KEY,
    nome                VARCHAR(500),
    classificacao_etaria VARCHAR(10),
    linguagens          TEXT[],
    desenvolvedores     TEXT[],
    distribuidores      TEXT[],
    preco               VARCHAR(50),
    metacritic_score    VARCHAR(20),
    categorias          TEXT[],
    genero              TEXT[],
    data_lancamento     VARCHAR(50),
    type                VARCHAR(50),
    review_score        INTEGER,
    total_reviews       INTEGER,
    total_negative      INTEGER,
    total_positive      INTEGER,
    review_score_desc   VARCHAR(100),
    detalhes_completos  JSONB,   -- payload completo da Steam API
    reviews_completos   JSONB,   -- payload completo de reviews
    ultima_atualizacao  TIMESTAMP DEFAULT NOW()
);
```

### 4.3 Sistema de Checkpoint

```sql
CREATE TABLE processing_checkpoint (
    pc_id       INTEGER,
    tipo        VARCHAR(20),  -- 'STEAM' | 'ITAD'
    indice      INTEGER,
    atualizado  TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (pc_id, tipo)
);
```

O checkpoint é salvo a cada batch processado. Em caso de reinício, o sistema retoma do índice salvo sem reprocessar dados já coletados.

---

## 5. Pipeline de Dados Detalhado

### 5.1 Fluxo Completo (`Process.execute`)

```
Etapa 1 — Coleta Steam
  PostgreSQLSteam.buscar_appids_desatualizados_otimizado()
    → AppIDs com ultima_atualizacao < NOW() - 90 dias
  Previsor.alimentar_banco_dados_raw_docker()
    → SteamClient.fetch_details_bulk_batched(appids)
    → SteamClient.fetch_reviews_bulk_batched(appids)
    → PostgreSQLSteam.inserir_dadosSteamRaw_Bulk(dados)
    → PostgreSQLCheckpoint.salvar_checkpoint(pc_id, índice, 'STEAM')

Etapa 2 — ETL
  ProcessadorETL.processar_lote_unificado(appids_desatualizados)
    → Lê steam_raw em batches de 1000
    → Aplica limpeza por domínio (limpeza_*.py)
    → Insere/atualiza steam_unificado

Etapa 3 — ITAD Lookup
  Previsor.alimentar_banco_dados_ITAD_docker()
    → ITADClient.lookup_appids(batch=200)
    → PostgreSQLITAD.inserir_mapping(appid, slug)

Etapa 4 — ITAD Histórico
  Previsor.alimentar_ITAD_historico_precos()
    → ITADClient.buscar_historico_precos(slug)
    → PostgreSQLITAD.inserir_itad_raw(historico)
    → PostgreSQLCheckpoint.salvar_checkpoint(pc_id, índice, 'ITAD')

Etapa 5 — Treinamento ML
  ProcessadorTreinamento.executar_treinamento()
    → Treinar_Modelos.executar_treinamento()
    → Persiste 6 modelos .joblib em resources/models/
```

### 5.2 Rate Limiting e Resiliência

| API | Estratégia | Delay entre batches |
|---|---|---|
| Steam Detalhes | 3 retries, backoff 240s por HTTP 429 | 240s |
| Steam Reviews | 3 retries, backoff 60s | 60s |
| SteamSpy | 20 páginas paralelas, retry 3x | Automático |
| ITAD Lookup | Batches de 200, delay 120s | 120s |
| ITAD Histórico | Sequencial com checkpoint | 2s por item |

---

## 6. Machine Learning

### 6.1 Problemas Modelados

| Tipo | Alvo | Descrição |
|---|---|---|
| Classificação | Direção de preço | `sobe` / `mantem` / `cai` (3 classes) |
| Regressão | Dias até desconto | Valor numérico contínuo |

### 6.2 Modelos Implementados

| Modelo | Tipo | Hiperparâmetros Principais |
|---|---|---|
| `LightGBMClassifier` | Classificação | `n_estimators=300`, `learning_rate=0.05`, `num_leaves=31`, early stopping 50 rounds |
| `XGBClassifier` | Classificação | `n_estimators=300`, `learning_rate=0.05`, `max_depth=8`, `objective=multi:softprob` |
| `RandomForestClassifier` | Classificação | `n_estimators=300`, `max_depth=12`, `n_jobs=-1` |
| `LGBMRegressor` | Regressão | `n_estimators=300`, `learning_rate=0.05`, early stopping 50 rounds |
| `XGBRegressor` | Regressão | `n_estimators=300`, `learning_rate=0.05`, `max_depth=8` |
| `LinearRegression` | Regressão | Baseline linear |

### 6.3 Features Utilizadas

**Features numéricas (de `steam_unificado`):**
- `preco_numerico` — preço convertido de string BR para float
- `metacritic_numerico` — score numérico
- `review_score`, `total_reviews`, `total_positive`, `total_negative`
- `taxa_positivas` — total_positive / total_reviews
- `popularidade` — log1p(total_reviews)
- `num_categorias`, `num_generos`, `num_linguagens`
- `dias_desde_lancamento`

**Features extraídas do JSONB (detalhes):**
- `num_conquistas`, `num_dlcs`, `num_screenshots`, `num_movies`
- `is_free`, `tem_demo`

**Features do histórico ITAD:**
- `num_promocoes`, `desconto_medio`, `desconto_maximo`
- `preco_mais_baixo`, `preco_mais_alto`
- `dias_desde_ultima_promo`

### 6.4 Split Temporal

```python
# Ordena por ultima_atualizacao (evita data leakage)
df_sorted = df.sort_values('ultima_atualizacao')
split_idx = int(len(df_sorted) * 0.8)

X_train = df_sorted[:split_idx]   # 80% mais antigos → treino
X_test  = df_sorted[split_idx:]   # 20% mais recentes → teste
```

### 6.5 Métricas de Avaliação

**Classificação:**
- Acurácia global
- Precisão macro (média entre classes, sem ponderar frequência)
- F1-Score macro (**métrica principal para TCC**)
- Matriz de confusão (CSV + PNG em `resources/relatorios/`)
- Detecção automática de overfitting (Δ acurácia treino/teste)

**Regressão:**
- RMSE — métrica principal (interpretável em "dias")
- MAE, MSE
- Plots: predito vs real, resíduos vs predito

### 6.6 Resultados da Última Execução (13/05/2026)

| Modelo | Acurácia | F1-Macro | Dataset |
|---|---|---|---|
| XGBoost | 98.7% | 0.7273 ✅ | 2.5M amostras |
| LightGBM | 98.6% | 0.6770 | 2.5M amostras |
| Random Forest | 98.6% | 0.6792 | 2.5M amostras |

| Modelo | RMSE (dias) | MAE (dias) |
|---|---|---|
| XGBoost | 47.19 ✅ | — |
| LightGBM | 47.46 | — |
| Linear | 50.05 | — |

### 6.7 Persistência de Modelos

Após cada treinamento, todos os 6 modelos são salvos em `resources/models/`:
```
modelo_classificacao_LightGBM_<timestamp>.joblib
modelo_classificacao_LightGBM_latest.joblib
modelo_classificacao_XGBoost_<timestamp>.joblib
modelo_classificacao_XGBoost_latest.joblib
modelo_classificacao_RandomForest_<timestamp>.joblib
modelo_classificacao_RandomForest_latest.joblib
modelo_regressao_LightGBM_<timestamp>.joblib
modelo_regressao_LightGBM_latest.joblib
modelo_regressao_XGBoost_<timestamp>.joblib
modelo_regressao_XGBoost_latest.joblib
modelo_regressao_LinearRegression_<timestamp>.joblib
modelo_regressao_LinearRegression_latest.joblib
```

Controlável via `.env`: `ML_SALVAR_MODELOS=False` desativa a persistência.

---

## 7. Configuração de Ambiente

### 7.1 Variáveis de Ambiente (`.env`)

| Variável | Tipo | Descrição |
|---|---|---|
| `DB_NAME` | string | Nome do banco PostgreSQL |
| `DB_USER` | string | Usuário do banco |
| `DB_PASSWORD` | string | Senha do banco |
| `DB_HOST` | string | Host do banco (ex: `127.0.0.1`) |
| `DB_PORT` | integer | Porta do banco (ex: `5432`) |
| `ITAD_API_KEY` | string | Chave de API do IsThereAnyDeal |
| `PC_ID` | integer | Identificador do PC (para processamento multi-PC) |
| `TOTAL_PCS` | integer | Total de PCs no cluster (para particionamento) |
| `ML_JANELA_DIAS` | integer | Janela de dados para treinamento (padrão: `90`) |
| `ML_TEST_SIZE` | float | Proporção para conjunto de teste (padrão: `0.2`) |
| `ML_MIN_REGISTROS_TREINO` | integer | Mínimo de registros para treinar (padrão: `1000`) |
| `ML_SALVAR_MODELOS` | bool | Persistir modelos .joblib (padrão: `True`) |
| `ML_RANDOM_STATE` | integer | Seed de reprodutibilidade (padrão: `42`) |
| `MATRIZ_CONFUSAO_PLOT` | string | Modo de plot: `save`, `show`, `save_show`, vazio=desligado |
| `MATRIZ_CONFUSAO_PLOT_DPI` | integer | DPI dos plots PNG (padrão: `300`) |
| `AMBIENTE` | string | `HML` (testes) ou `PRD` (produção) |
| `BATCH_TESTE` | integer | Tamanho do batch em modo HML (padrão: `20`) |
| `etl_processar_todos_dados` | bool | Se True, ETL reprocessa todos os registros |

### 7.2 Suporte Multi-PC

O sistema suporta distribuição de carga entre múltiplos computadores:

```
PC 1 (PC_ID=1, TOTAL_PCS=2) → processa AppIDs pares
PC 2 (PC_ID=2, TOTAL_PCS=2) → processa AppIDs ímpares
```

A partição é realizada no `PostgreSQLSteam.buscar_appids_nao_processados()` via filtro `appid % TOTAL_PCS = PC_ID - 1`.

---

## 8. Infraestrutura

### 8.1 Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Runtime | Python 3.10+ |
| Banco de dados | PostgreSQL 15 (Docker) |
| Coleta assíncrona | `aiohttp` 3.10 |
| Retry / backoff | `tenacity` 8.2 |
| ML | `scikit-learn` 1.7, `xgboost` 3.0, `lightgbm` 4.6 |
| Dados | `pandas` 2.3, `numpy` |
| Serialização | `joblib` |
| Visualização | `matplotlib` 3.10, `seaborn` 0.13 |
| Texto | `unidecode` 1.4 |
| Config | `python-dotenv` 1.0 |
| Testes | `pytest` 8.0 |
| Qualidade | `black` 24.8, `ruff` 0.6 |

### 8.2 Docker

O PostgreSQL é iniciado automaticamente via `docker-compose` em `docker/`:

```yaml
# docker/docker-compose.yml (resumo)
services:
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    volumes: ["./volumes/db:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
```

`Settings.start_docker_postgres()` verifica o status do container antes de cada execução. Se não estiver `healthy`, tenta iniciar e aguarda até 60s.

---

## 9. Estrutura de Diretórios

```
Projeto_TCC_CC/
├── prj_TCC_PREVISOR_STEAM/
│   ├── bot.py                          # Entry point
│   ├── classes/
│   │   ├── api/                        # Clientes de API externos
│   │   │   ├── steam_api.py
│   │   │   ├── steamspy_api.py
│   │   │   ├── itad_api.py
│   │   │   └── local_steam.py
│   │   ├── framework/                  # Orquestração do bot
│   │   │   ├── AllSettings.py
│   │   │   ├── Initialization.py
│   │   │   ├── InitApplication.py
│   │   │   ├── Loop.py
│   │   │   ├── Process.py
│   │   │   ├── End.py
│   │   │   └── Close.py
│   │   ├── data/                       # Camada de dados
│   │   │   ├── previsor.py
│   │   │   └── repositories/
│   │   │       ├── postgre_generico.py
│   │   │       ├── postgre_steam.py
│   │   │       ├── postgre_itad.py
│   │   │       ├── postgre_bdgeral.py
│   │   │       ├── postgre_checkpoint.py
│   │   │       └── postgre_criar_tabela.py
│   │   ├── limpeza/                    # ETL e limpeza
│   │   │   ├── ProcessadorETL.py
│   │   │   ├── limpeza.py
│   │   │   └── limpeza_*.py (11 arquivos por domínio)
│   │   ├── treinamento/                # Machine Learning
│   │   │   ├── ProcessadorTreinamento.py
│   │   │   ├── treinar_modelos.py
│   │   │   └── normalizar_modelos.py
│   │   ├── utils/
│   │   │   └── GetTask.py
│   │   └── tests/                      # Testes unitários
│   │       ├── conftest.py
│   │       └── test_*.py (11 arquivos)
│   └── resources/
│       ├── dados/                      # Cache e datasets
│       │   └── steam_applist.json
│       ├── docs/                       # Documentação técnica
│       ├── logs/
│       │   └── app.log
│       ├── models/                     # Modelos treinados (.joblib)
│       ├── relatorios/                 # Métricas e plots
│       └── SQL/                        # Scripts DDL
├── docker/
│   └── docker-compose.yml
├── .env
├── requirements.txt
├── setup.py
├── pytest.ini
├── README.md
├── Checklist.md                        # Checklist ML (Géron)
└── VERSION
```

---

## 10. Tratamento de Erros

| Situação | Comportamento |
|---|---|
| HTTP 429 (rate limit Steam) | Retry 3x com espera de 240s; batch marcado como `http429` |
| HTTP 404 no endpoint legado Steam | Fallback automático para SteamSpy |
| Docker não disponível | `InitApplication` lança exceção e aborta |
| Dataset vazio para treinamento | Log de erro, treinamento pulado sem exceção |
| Erro em etapa do `Process` | Etapa isolada por `try/except`; próximas etapas continuam |
| Falha após `max_tentativas` no Loop | Exceção propagada e capturada pelo `bot.py` |
| AppID retorna `success: false` | Salvo como `"AUSENTE"` no campo JSONB; não quebra o ETL |

---

## 11. Pendências e Roadmap

### 11.1 Pendências Técnicas (backlog imediato)

| Item | Prioridade |
|---|---|
| `Close.py` e `End.py` — implementar limpeza real (fechar pool de conexões) | Média |
| `postgre_criar_tabela.py` — integrar ao fluxo de bootstrap (auto-create tables) | Média |
| Testes unitários dos módulos de limpeza (`limpeza_*.py`) | Média |

### 11.2 Melhorias Futuras (backlog TCC)

| Item | Descrição |
|---|---|
| Hyperparameter Tuning | Optuna ou GridSearch para otimizar XGBoost |
| SHAP Values | Explicabilidade dos modelos para o artigo |
| Cross-validation temporal | `TimeSeriesSplit` do sklearn |
| API REST de predições | FastAPI expondo os modelos `_latest.joblib` |
| Dashboard Streamlit | Visualização interativa das predições |
| Notebook de análise exploratória | Para a apresentação do TCC |

---

*Documento gerado em 13/05/2026 com base no estado real do código e logs de execução.*
