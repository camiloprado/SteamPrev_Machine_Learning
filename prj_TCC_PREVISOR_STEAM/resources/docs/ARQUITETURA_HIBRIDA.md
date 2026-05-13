# Arquitetura de Dados e Execução

## Objetivo desta arquitetura

A arquitetura do projeto foi desenhada para processar alto volume de dados de jogos com foco em:
- estabilidade de execução
- reprocessamento controlado
- separação entre coleta, ETL e treinamento
- resiliência via checkpoint e retry com backoff

## Visão geral

```text
Fontes externas
  -> Steam API / SteamSpy / ITAD
Coleta assíncrona
  -> clients em classes/api/
Persistência operacional
  -> PostgreSQL local (Docker)
Processamento
  -> ETL + limpeza + unificação
Treinamento ML
  -> modelos de classificação e regressão
Saída
  -> resources/relatorios/ (métricas, plots)
  -> resources/models/ (modelos .joblib)
```

## Camadas do sistema

### 1) Orquestração

Pasta: `classes/framework/`

- `InitApplication.py`: bootstrap — inicia Docker, atualiza índice de apps (SteamSpy), cria fila
- `Loop.py`: ciclo de tarefas — consome a fila e chama Process a cada iteração
- `Process.py`: **pipeline completo** — coleta Steam, ETL, ITAD lookup, histórico de preços, treinamento ML
- `End.py`: finalização e cleanup
- `AllSettings.py`: configuração de ambiente, log e API

### 2) Integração com APIs

Pasta: `classes/api/`

- `steam_api.py`: detalhes e reviews (detalhes batch assíncrono, retry 3x com 240s)
- `steamspy_api.py`: fallback da listagem de apps (paralelização de 20 páginas simultâneas)
- `itad_api.py`: lookup e histórico de preço
- `local_steam.py`: cache local de app list (`resources/dados/steam_applist.json`)

### 3) Persistência

Pasta: `classes/data/repositories/`

- `postgre_steam.py`: operações em `steam_raw` e `steam_generico`
- `postgre_itad.py`: operações em `itad_raw` e `steam_itad_mapping`
- `postgre_generico.py`: pool de conexões compartilhado e operações gerais
- `postgre_bdgeral.py`: tabela `steam_geral` (base unificada para ML)
- `postgre_checkpoint.py`: sistema de checkpoint por tipo (STEAM, ITAD) e PC_ID

Tabelas no banco:
- `steam_generico` — índice operacional de AppIDs
- `steam_raw` — dados brutos JSONB (detalhes + reviews)
- `steam_unificado` — dados ETL estruturados (fonte principal de ML)
- `itad_raw` — histórico de preços ITAD
- `steam_itad_mapping` — mapeamento Steam ↔ ITAD
- `processing_checkpoint` — retomada de execução por etapa

### 4) ETL e limpeza

- `classes/limpeza/ProcessadorETL.py` — orquestração ETL (steam_raw → steam_unificado)
- `classes/limpeza/limpeza_dados.py` — regras de limpeza por domínio
- `classes/data/previsor.py` — alimentação dos bancos raw (Steam e ITAD)

### 5) Machine Learning

Pasta: `classes/treinamento/`

- `treinar_modelos.py` — classe `Treinar_Modelos` (LightGBM, XGBoost, RF, Regressão Linear)
- `normalizar_modelos.py` — normalização dos dados e splits treino/teste
- `ProcessadorTreinamento.py` — orquestrador de alto nível chamado pelo `Process`
- `treinamento.py` — classe `TreinarModelo` com pipeline de feature engineering

Modelos utilizados:
- LightGBM (classificação + regressão)
- XGBoost (classificação + regressão)
- Random Forest (classificação)
- Regressão Linear (regressão)

Saída após treinamento:
- `resources/relatorios/` — CSVs e PNGs (matrizes de confusão, resíduos, predito vs real)
- `resources/models/` — arquivos `.joblib` com timestamp e cópia `_latest`

## Fluxo de execução (alto nível)

```
InitApplication.execute()
  └─ Settings.start_docker_postgres()         # garante container healthy
  └─ GetTask.abandona_fila()                  # limpa fila anterior
  └─ GetTask.criar_fila()
       └─ LocalClient.find_app_list()         # busca lista de apps (SteamSpy fallback)
       └─ PostgreSQLSteam.inserir_dadosSteamGenerico()  # atualiza steam_generico
       └─ _var_listTaskQueue = [1]            # 1 tarefa na fila

Loop.execute()
  └─ while fila não vazia:
       └─ Process.execute()                   # pipeline completo por iteração
            ├─ Etapa 1: alimentar_banco_dados_raw_docker()   # coleta Steam
            ├─ Etapa 2: ProcessadorETL.processar_lote_unificado()  # ETL
            ├─ Etapa 3: alimentar_banco_dados_ITAD_docker()  # ITAD lookup
            ├─ Etapa 4: alimentar_ITAD_historico_precos()    # histórico
            └─ Etapa 5: ProcessadorTreinamento.executar_treinamento()  # ML
```

## Observação sobre suporte multi-PC

O sistema suporta distribuição via variáveis `PC_ID` e `TOTAL_PCS` no `.env`.
O checkpoint garante que cada PC retome do ponto onde parou sem reprocessar AppIDs já concluídos.

