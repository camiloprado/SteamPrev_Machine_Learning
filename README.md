# Previsor Steam

Sistema para análise, coleta e previsão de dados de jogos da Steam, integrando informações da API Steam, IsThereAnyDeal (ITAD) e banco de dados PostgreSQL.

## 🎯 O Que Este Sistema Faz?

O **Previsor Steam** automatiza a coleta massiva de dados de jogos da plataforma Steam, incluindo detalhes técnicos, avaliações, preços e histórico. Os dados são armazenados em PostgreSQL para análises de mercado, tendências e estudos acadêmicos.

**📖 Para uma explicação completa e detalhada**, consulte: [O Que o Sistema Faz?](resources/docs/O_QUE_O_SISTEMA_FAZ.md)

## Funcionalidades

- **Coleta Automática**: Busca dados de jogos da Steam (detalhes, reviews, preços)
- **Histórico de Preços**: Integração com ITAD para rastreamento de promoções
- **Armazenamento Robusto**: PostgreSQL com inserções otimizadas em lote
- **Performance**: Processamento assíncrono para múltiplas requisições simultâneas
- **Qualidade de Dados**: Limpeza e normalização automática dos dados coletados
- **Multi-PC**: Suporte para coleta distribuída em várias máquinas

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

Configure as variáveis de conexão e API no arquivo `.env` na raiz do projeto:

### Configurações de Banco de Dados
```env
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_HOST=127.0.0.1
DB_PORT=5432
```

### Configurações de Processamento Multi-PC
```env
PC_ID=1                    # Identificador deste computador (1, 2, 3...)
TOTAL_PCS=1                # Número total de computadores processando
RANGE_PROCESSAMENTO_APPIDS_RAW=1000
RANGE_PROCESSAMENTO_ITAD_RAW=5000
```

### Configurações de Machine Learning (Novo!)
```env
ML_TREINAMENTO_AUTO=True   # Ativar treinamento automático a cada 90 dias
ML_INTERVALO_DIAS=90       # Intervalo mínimo entre treinamentos
ML_ALGORITMO_PADRAO=xgboost # Algoritmo padrão (randomforest, xgboost, lightgbm, todos)
```

O sistema agora executa **treinamento automático de ML** durante a execução do `GetTask.criar_fila()`:
- ✅ Verifica se há dados suficientes (>1000 registros nos últimos 90 dias)
- ✅ Detecta se último treinamento foi há mais de 90 dias
- ✅ Executa treinamento automaticamente usando XGBoost (padrão)
- ✅ Registra métricas em `ml_treinamento_historico`


## Como executar

1. Ative o ambiente virtual:
	```bash
	.venv\Scripts\activate
	```
2. Execute o bot principal (coleta de dados automática):
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

### Estrutura Otimizada (Pós-otimização 2026-01-05)

O sistema utiliza PostgreSQL com as seguintes tabelas:

| Tabela | Tamanho | Registros | Propósito |
|--------|---------|-----------|-----------|
| `steam_generico` | 25 MB | 276,562 | Índice rápido de AppIDs |
| `steam_raw` | 1226 MB | 276,564 | Dados brutos JSONB da Steam |
| **`steam_unificado`** | **1599 MB** | **229,672** | **Fonte principal para ML** (estruturado + JSONB) |
| `itad_raw` | 178 MB | 227,261 | Histórico de preços ITAD |
| `steam_itad_mapping` | 56 MB | 227,856 | Mapeamento AppID ↔ ITAD |
| `ml_treinamento_historico` | 32 kB | - | Registro de treinamentos ML |

**Total**: ~3.1 GB

### Criação Inicial

```sql
CREATE DATABASE postgres;
```

O sistema criará as tabelas automaticamente na primeira execução. A tabela `ml_treinamento_historico` registra:
- Data e janela temporal de cada treinamento (90 dias)
- Algoritmo utilizado (RandomForest, XGBoost, LightGBM)
- Métricas de performance (acurácia, F1-score, RMSE)
- Parâmetros utilizados (JSONB)

### Consultas Úteis

```sql
-- Ver último treinamento ML
SELECT data_treinamento, algoritmo, acuracia, f1_score 
FROM ml_treinamento_historico 
ORDER BY data_treinamento DESC LIMIT 1;

-- Dados disponíveis para próximo treinamento
SELECT COUNT(*) FROM steam_unificado 
WHERE ultima_atualizacao >= NOW() - INTERVAL '90 days';
```

## 📚 Documentação Adicional

Para mais informações sobre o sistema:

- **[📖 O Que o Sistema Faz?](resources/docs/O_QUE_O_SISTEMA_FAZ.md)** - Explicação completa e detalhada do sistema
- **[🏗️ Arquitetura do Sistema](resources/docs/ARQUITETURA_SISTEMA.md)** - Diagramas técnicos e componentes
- **[❓ Perguntas Frequentes](resources/docs/PERGUNTAS_FREQUENTES.md)** - Respostas rápidas sobre o sistema
- **[🎯 Quick Start ITAD](resources/docs/QUICK_START_ITAD.md)** - Guia de inserção de dados ITAD
- **[💻 Configuração Multi-PC](resources/docs/CONFIGURACAO_MULTI_PC.md)** - Setup distribuído
- **[📦 Guia de Instalação](resources/docs/GUIA_INSTALACAO_OUTRO_PC.md)** - Como instalar em outro PC

## Licença

Este projeto é acadêmico e sem fins lucrativos.

---

> Desenvolvido para Trabalho de Conclusão de Curso (TCC) - Ciência da Computação
