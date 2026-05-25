# 🎮 O Que o Sistema Faz?

## 📋 Visão Geral

O **Previsor Steam** é um sistema automatizado de coleta, análise e armazenamento de dados de jogos da plataforma Steam. Desenvolvido como Trabalho de Conclusão de Curso (TCC) em Ciência da Computação, o sistema integra múltiplas fontes de dados para criar uma base completa sobre jogos, incluindo informações de preços, avaliações, históricos e características.

## 🎯 Objetivo Principal

Coletar, organizar e armazenar dados detalhados de jogos da Steam para possibilitar análises de mercado, previsões de tendências e estudos sobre a indústria de games.

## 🔄 Como o Sistema Funciona

### 1. **Coleta de Dados da Steam**

O sistema busca informações diretamente da API oficial da Steam, incluindo:

- **Detalhes dos Jogos**: Nome, desenvolvedores, distribuidores, data de lançamento
- **Características**: Categorias, gêneros, idiomas suportados, classificação etária
- **Preços**: Valores atuais e formatados para diferentes moedas
- **Avaliações (Reviews)**: Score de reviews, total de avaliações positivas/negativas, descrição do score
- **Metacritic**: Pontuação de crítica especializada quando disponível

### 2. **Integração com IsThereAnyDeal (ITAD)**

Para enriquecer os dados com histórico de preços, o sistema se integra com a plataforma ITAD:

- Busca histórico completo de preços de cada jogo
- Identifica promoções e descontos ao longo do tempo
- Permite análises de tendências de precificação
- Detecta jogos que precisam de atualização de dados (90 dias sem atualizar)

### 3. **Armazenamento em PostgreSQL**

Todos os dados coletados são armazenados de forma estruturada em um banco de dados PostgreSQL:

- **Tabelas Raw**: Dados brutos da API Steam e ITAD
- **Dados Processados**: Informações limpas e organizadas para análise
- **Inserção em Lotes**: Otimizado para processar milhares de jogos eficientemente (bulk insert)
- **Controle de Duplicatas**: Evita inserir dados já existentes

### 4. **Processamento e Limpeza**

O sistema realiza tratamento dos dados coletados:

- Normalização de datas em diferentes formatos
- Limpeza de strings (remoção de HTML, caracteres especiais)
- Validação de tipos de dados
- Filtragem de jogos relevantes (pagos, não demos)

### 5. **Arquitetura Multi-PC**

O sistema suporta execução distribuída:

- Múltiplas máquinas podem coletar dados simultaneamente
- Cada máquina processa um subconjunto de jogos (divisão por PC ID)
- Compartilhamento de carga para acelerar coleta em larga escala
- Ideal para processar centenas de milhares de jogos

## 📊 Fluxo de Trabalho Completo

```
1. INICIALIZAÇÃO
   └─> Carrega configurações (.env, AllSettings)
   └─> Conecta ao PostgreSQL
   └─> Inicializa clientes de API (Steam, ITAD)

2. BUSCA DE JOGOS
   └─> Consulta lista de AppIDs da Steam
   └─> Filtra jogos já processados
   └─> Divide trabalho entre PCs (se multi-PC)

3. COLETA DE DADOS
   └─> Para cada jogo (AppID):
       ├─> Busca detalhes na Steam API
       ├─> Busca reviews na Steam API
       ├─> Busca histórico de preços no ITAD
       └─> Aguarda delays (respeito aos rate limits)

4. PROCESSAMENTO
   └─> Filtra apenas jogos pagos
   └─> Limpa e normaliza dados
   └─> Valida informações obrigatórias
   └─> Organiza em estrutura para BD

5. ARMAZENAMENTO
   └─> Insere dados raw no PostgreSQL
   └─> Registra em lotes (batches) para performance
   └─> Gera logs de progresso e erros

6. LOOP CONTÍNUO
   └─> Processa fila de tarefas
   └─> Tenta novamente em caso de erros (max_tentativas)
   └─> Continua até processar todos os jogos

7. ENCERRAMENTO
   └─> Fecha conexões com banco de dados
   └─> Salva estatísticas finais
   └─> Gera relatório de execução
```

## 🛠️ Componentes Principais

### Bot (`bot.py`)
Orquestrador principal que gerencia todo o ciclo de vida do sistema: inicialização, loop de processamento e encerramento.

### Previsor (`previsor.py`)
Coração do sistema - responsável pela lógica de coleta, processamento e armazenamento dos dados.

### Steam API (`steam_api.py`)
Cliente assíncrono para comunicação com a API da Steam, respeitando rate limits e tratando erros.

### PostgreSQL (`postgre.py`)
Gerenciador de todas as operações de banco de dados: consultas, inserções em lote, buscas otimizadas.

### Limpeza de Dados (`limpeza_dados.py`)
Módulo especializado em normalizar e validar dados coletados antes do armazenamento.

### Loop e Process (`Loop.py`, `Process.py`)
Gerenciam a fila de tarefas e o processamento sequencial com tratamento de erros e tentativas.

## 💡 Casos de Uso

### 1. **Primeira Coleta Completa**
Buscar e armazenar dados de todos os jogos disponíveis na Steam (milhares de jogos).

### 2. **Atualização de Dados ITAD**
Atualizar histórico de preços de jogos que não têm dados recentes (> 90 dias).

### 3. **Análise de Mercado**
Pesquisadores podem consultar o banco de dados para estudos sobre:
- Tendências de precificação
- Popularidade de gêneros
- Correlação entre reviews e vendas
- Estratégias de desenvolvedores

### 4. **Coleta Distribuída**
Em ambientes com múltiplos computadores, dividir o trabalho para acelerar a coleta massiva de dados.

## 📈 Estatísticas e Logs

O sistema mantém registros detalhados:

- **Logs de Progresso**: Quantos jogos foram processados, tempo de execução
- **Logs de Erro**: Falhas de API, problemas de conexão, dados inválidos
- **Estatísticas**: Taxa de sucesso, delays aplicados, tentativas de retry
- **Relatórios**: Resumo final com totais e métricas de execução

## 🔐 Segurança e Boas Práticas

- **Rate Limiting**: Respeita limites de requisições das APIs
- **Tratamento de Erros**: Tentativas múltiplas com backoff
- **Validação de Dados**: Verifica integridade antes de inserir no BD
- **Logs Auditáveis**: Rastreamento completo de todas as operações
- **Configuração Segura**: Credenciais em variáveis de ambiente (.env)

## 🚀 Tecnologias Utilizadas

- **Python 3.10+**: Linguagem principal
- **PostgreSQL**: Banco de dados relacional
- **asyncio/aiohttp**: Requisições assíncronas para melhor performance
- **Steam Web API**: Fonte oficial de dados da Steam
- **IsThereAnyDeal API**: Histórico de preços de jogos
- **Docker** (opcional): Containerização para ambientes isolados

## 📚 Para Desenvolvedores

Se você quer entender como o código funciona em detalhes:

1. **Comece por**: `bot.py` - ponto de entrada do sistema
2. **Explore**: `previsor.py` - lógica principal de coleta
3. **Veja**: `postgre.py` - como os dados são armazenados
4. **Entenda**: `AllSettings.py` - todas as configurações disponíveis

## 🎓 Contexto Acadêmico

Este é um projeto de TCC que demonstra:

- Integração com APIs externas
- Processamento assíncrono em Python
- Modelagem e otimização de banco de dados
- Arquitetura de sistemas distribuídos
- Coleta e análise de dados em larga escala

---

> **Desenvolvido para TCC - Ciência da Computação**  
> Sistema acadêmico e sem fins lucrativos
