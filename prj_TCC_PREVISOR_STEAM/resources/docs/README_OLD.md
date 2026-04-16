# Documentacao Tecnica Consolidada

Este documento centraliza a navegacao para a documentacao tecnica do projeto.

## Comece por aqui

- Arquitetura e execucao: [ARQUITETURA_HIBRIDA.md](ARQUITETURA_HIBRIDA.md)
- Guia rapido ITAD: [QUICK_START_ITAD.md](QUICK_START_ITAD.md)
- Metodos ITAD detalhados: [RESUMO_METODOS_ITAD.md](RESUMO_METODOS_ITAD.md)
- Otimizacoes SQL: [OTIMIZACAO_CONSULTAS_SQL.md](OTIMIZACAO_CONSULTAS_SQL.md)
- Melhorias aplicadas: [MELHORIAS_IMPLEMENTADAS.md](MELHORIAS_IMPLEMENTADAS.md)
- Backlog: [Backlog.md](Backlog.md)

## Estrutura real do codigo

Pacote principal: prj_TCC_PREVISOR_STEAM

- classes/framework: ciclo de vida da aplicacao
- classes/api: integracoes externas
- classes/data/repositories: acesso a dados
- classes/limpeza: regras de limpeza e ETL
- classes/treinamento: treinamento e avaliacao
- classes/utils: tarefas e utilitarios
- resources: dados, logs, docs e artefatos

## Dependencias principais

- Dados e ETL: pandas, psycopg, aiohttp, tenacity
- ML: scikit-learn, xgboost, lightgbm
- Qualidade: pytest, black, ruff

Dependencias completas: ../../requirements.txt

## Estado operacional (resumo)

Com base em resources/logs/app.log:
- fallback para SteamSpy ativo quando endpoint legado da Steam falha
- execucao depende do estado do Docker em ambientes que iniciam container automaticamente
- pipeline de treinamento esta integrado ao fluxo de tarefas

## Nota

Este arquivo substitui a antiga funcao de README legado e passa a servir como indice tecnico de navegacao.
