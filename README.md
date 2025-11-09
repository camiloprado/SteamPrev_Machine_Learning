# Previsor Steam

Sistema para análise, coleta e previsão de dados de jogos da Steam, integrando informações da API Steam, IsThereAnyDeal (ITAD) e banco de dados PostgreSQL.

## Funcionalidades

- Coleta de dados de jogos da Steam (detalhes, reviews, preços)
- Integração com ITAD para histórico de preços
- Armazenamento dos dados em PostgreSQL
- Processamento assíncrono para maior performance
- Limpeza e organização dos dados coletados

## Estrutura do Projeto

```
prj_TCC_PREVISOR_STEAM/
	bot.py
	classes/
		api/
			steam_api.py
			steam_appid_lookup.py
		framework/
			AllSettings.py
			Close.py
			End.py
			InitApplication.py
			Initialization.py
			Loop.py
			Process.py
		SQL/
			postgre.py
		utils/
			GetTask.py
		limpeza/
			limpeza_dados.py
	resources/
		dados/
		docs/
		relatorios/
requirements.txt
setup.py
```

## Requisitos

- Python 3.10+
- PostgreSQL
- Instalar dependências:
  ```bash
  pip install -r requirements.txt
  ```

## Configuração

Configure as variáveis de conexão e API em `AllSettings.py`.


## Como executar

1. Ative o ambiente virtual:
	```bash
	.venv\Scripts\activate
	```
2. Execute o bot principal:
	```bash
	python prj_TCC_PREVISOR_STEAM/bot.py
	```

## Logs

O sistema gera arquivos de log em `prj_TCC_PREVISOR_STEAM/resources/logs/` para registrar eventos, erros, progresso dos batches e estatísticas de execução. Os logs são úteis para:

- Monitorar o andamento da coleta e processamento dos dados
- Identificar falhas de conexão, limites de API ou dados ausentes
- Auditar configurações utilizadas (.env, batch size, delays, etc.)
- Depurar problemas e analisar resultados

Você pode configurar o nível de detalhamento dos logs (INFO, WARNING, ERROR) em `AllSettings.py` ou diretamente no código principal. Para visualizar os logs, basta abrir os arquivos `.log` na pasta indicada.

## Banco de Dados

Crie o banco de dados PostgreSQL antes de rodar o sistema:
```sql
CREATE DATABASE previsao_steam;
```

## Licença

Este projeto é acadêmico e sem fins lucrativos.

---

> Desenvolvido para Trabalho de Conclusão de Curso (TCC) - Ciência da Computação
