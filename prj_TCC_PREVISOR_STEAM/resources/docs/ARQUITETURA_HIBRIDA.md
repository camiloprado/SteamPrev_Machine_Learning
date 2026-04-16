# Arquitetura de Dados e Execucao

## Objetivo desta arquitetura

A arquitetura do projeto foi desenhada para processar alto volume de dados de jogos com foco em:
- estabilidade de execucao
- reprocessamento controlado
- separacao entre coleta, ETL e treinamento

## Visao geral

```text
Fontes externas
  -> Steam API / SteamSpy / ITAD
Coleta assíncrona
  -> clients em classes/api
Persistencia operacional
  -> PostgreSQL local (Docker quando habilitado)
Processamento
  -> ETL + limpeza + unificacao
Treinamento ML
  -> modelos de classificacao e regressao
```

## Camadas do sistema

### 1) Orquestracao

Pasta principal: classes/framework

- Initialization: bootstrap do sistema
- Loop: ciclo de tarefas
- End: finalizacao
- AllSettings: configuracao de ambiente, log e API

### 2) Integracao com APIs

Pasta principal: classes/api

- steam_api.py: detalhes e reviews
- steamspy_api.py: fallback da listagem de apps
- itad_api.py: lookup e historico de preco
- local_steam.py: cache local de app list

### 3) Persistencia

Pastas principais: classes/data/repositories

- steam_raw: dados de origem
- steam_generico: indice operacional
- itad_raw: dados ITAD
- steam_itad_mapping: mapeamento Steam x ITAD
- steam_geral: base unificada para treinamento
- processing_checkpoint: retomada de execucao por etapa

### 4) ETL e limpeza

- classes/limpeza/ProcessadorETL.py
- classes/scripts/ProcessadorLimpeza.py
- classes/limpeza/* (regras por atributo)

### 5) Machine Learning

Pasta principal: classes/treinamento

- treinamento.py
- ProcessadorTreinamento.py
- treinar_modelos.py

Modelos utilizados:
- LightGBM
- XGBoost
- Random Forest
- Regressao linear

## Fluxo de execucao (alto nivel)

1. Carga da lista de apps (com fallback local/SteamSpy)
2. Identificacao de AppIDs pendentes/desatualizados
3. Coleta dos dados Steam e ITAD
4. ETL para base consolidada
5. Atualizacao de steam_geral
6. Treinamento automatico quando aplicavel

## Estado recente observado no log

Arquivo: resources/logs/app.log

Pontos importantes da execucao mais recente observada:
- fallback de endpoint Steam funcionando
- ocorrencias de indisponibilidade de Docker em algumas execucoes
- treinamento iniciado com base steam_geral carregada
- falha pontual por variavel local nao inicializada em alimentar_tabela_Geral

## Observacao sobre documento legado

Este arquivo substitui a visao antiga de arquitetura hibrida com Supabase como caminho principal. O fluxo operacional atual observado no codigo e no log e centrado em PostgreSQL local.
