# Previsor Steam

Projeto de TCC em Ciência da Computação voltado para engenharia de dados e machine learning aplicado ao ecossistema Steam.

## Sobre o projeto

O sistema coleta dados de jogos em larga escala (Steam API, SteamSpy e ITAD), transforma os dados em uma base analítica e treina modelos preditivos para apoiar decisões de preço e potencial de sucesso.

Pontos centrais do trabalho:
- Pipeline de dados com foco em volume e resiliência
- Integração assíncrona com múltiplas fontes externas
- ETL para padronização de dados brutos e semiestruturados
- Treinamento de modelos (LightGBM, XGBoost, Random Forest e regressão)

## Destaques técnicos

- Processamento em lotes com ajuste dinâmico
- Retry com backoff para APIs externas
- Checkpoint para retomada de execução
- PostgreSQL local como núcleo operacional
- Limpeza e transformação orientadas a reprocessamento

## Stack e dependências

- Linguagem: Python 3.10+
- Dados: PostgreSQL
- ML: scikit-learn, LightGBM, XGBoost
- Processamento: pandas, aiohttp, tenacity
- Qualidade: pytest, ruff, black

Dependências completas em [requirements.txt](requirements.txt).

## Arquitetura e documentação

A documentação foi organizada por assunto em arquivos já existentes no repositório:

- Arquitetura e fluxo operacional: [prj_TCC_PREVISOR_STEAM/resources/docs/ARQUITETURA_HIBRIDA.md](prj_TCC_PREVISOR_STEAM/resources/docs/ARQUITETURA_HIBRIDA.md)
- Guia operacional ITAD (rápido): [prj_TCC_PREVISOR_STEAM/resources/docs/QUICK_START_ITAD.md](prj_TCC_PREVISOR_STEAM/resources/docs/QUICK_START_ITAD.md)
- Métodos ITAD (detalhado): [prj_TCC_PREVISOR_STEAM/resources/docs/RESUMO_METODOS_ITAD.md](prj_TCC_PREVISOR_STEAM/resources/docs/RESUMO_METODOS_ITAD.md)
- Otimizações SQL: [prj_TCC_PREVISOR_STEAM/resources/docs/OTIMIZACAO_CONSULTAS_SQL.md](prj_TCC_PREVISOR_STEAM/resources/docs/OTIMIZACAO_CONSULTAS_SQL.md)
- Melhorias implementadas: [prj_TCC_PREVISOR_STEAM/resources/docs/MELHORIAS_IMPLEMENTADAS.md](prj_TCC_PREVISOR_STEAM/resources/docs/MELHORIAS_IMPLEMENTADAS.md)
- Backlog de produto e roadmap técnico: [prj_TCC_PREVISOR_STEAM/resources/docs/Backlog.md](prj_TCC_PREVISOR_STEAM/resources/docs/Backlog.md)
- Documentação técnica consolidada: [prj_TCC_PREVISOR_STEAM/resources/docs/README_OLD.md](prj_TCC_PREVISOR_STEAM/resources/docs/README_OLD.md)

## Artigo e base acadêmica

- Referencial e estrutura do artigo: [prj_TCC_PREVISOR_STEAM/resources/docs/Referencial_teorico.md](prj_TCC_PREVISOR_STEAM/resources/docs/Referencial_teorico.md)

## Estado atual (com base no log mais recente)

Referência: [prj_TCC_PREVISOR_STEAM/resources/logs/app.log](prj_TCC_PREVISOR_STEAM/resources/logs/app.log)

Resumo objetivo do cenário observado:
- Endpoint antigo de app list da Steam retorna 404; fallback para SteamSpy está ativo
- Há execuções que falham ao iniciar Docker quando o engine não está disponível
- Após ambiente saudável, o pipeline volta a rodar e carrega dados de treino
- Existe falha registrada em alimentar steam_geral por variável local não inicializada em execução específica

## Execução local (passo a passo)

### 1) Pré-requisitos

- Python 3.10+
- Docker Desktop (ou Docker Engine)
- Git (opcional)

### 2) Clonar o projeto

```bash
git clone https://github.com/camiloprado/Projeto_TCC_CC.git
cd Projeto_TCC_CC
```

### 3) Criar e ativar ambiente virtual

Windows PowerShell:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/Mac:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4) Instalar dependências

```bash
pip install -r requirements.txt
```

### 5) Configurar variáveis de ambiente (.env)

Crie ou ajuste o arquivo `.env` na raiz do projeto com os campos mínimos:

```properties
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=projetotccADMIN
DB_HOST=localhost
DB_PORT=5432

# Obrigatória para fluxo ITAD
ITAD_API_KEY=sua_chave_itad
```

Observações:
- O sistema usa fallback local para a lista de apps da Steam quando o endpoint antigo retorna 404.
- Sem `ITAD_API_KEY`, a etapa de integração ITAD não funciona corretamente.

### 6) Subir PostgreSQL (Docker)

Na raiz do projeto:

```bash
docker compose -f docker/docker-compose.yml up -d db
```

Verifique se o container está ativo:

```bash
docker ps
```

### 7) Executar o projeto

```bash
python -m prj_TCC_PREVISOR_STEAM.bot
```

### 8) Validar execução pelo log

Arquivo de log:
- `prj_TCC_PREVISOR_STEAM/resources/logs/app.log`

Sinais esperados:
- Conexão com banco estabelecida em `localhost:5432`
- Mensagem de fallback local da app list da Steam (quando houver 404 no endpoint legado)
- Progresso de processamento em lotes

### 9) Troubleshooting rápido

- Erro `Connection refused` no PostgreSQL:
	- Inicie o Docker Desktop
	- Suba novamente o serviço `db`
	- Confirme `DB_HOST` e `DB_PORT` no `.env`
- Erro de endpoint Steam 404:
	- Comportamento esperado no estado atual; o projeto utiliza fallback local
- Erros de coluna SQL em scripts de diagnóstico ITAD:
	- Revise scripts utilitários de diagnóstico antes de usar em produção

## Autor

Camilo Prado  
TCC - Ciência da Computação
