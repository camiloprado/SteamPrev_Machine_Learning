# 🏗️ Arquitetura do Sistema Previsor Steam

## 📐 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        PREVISOR STEAM                            │
│                     (Bot Principal - bot.py)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ├──> 1. INITIALIZATION (Initialization.py)
                         │    └─> Carrega configurações (AllSettings.py)
                         │    └─> Conecta PostgreSQL
                         │    └─> Inicializa APIs (Steam, ITAD)
                         │
                         ├──> 2. LOOP (Loop.py)
                         │    └─> Carrega fila de tarefas (GetTask.py)
                         │    └─> Processa cada tarefa
                         │    └─> Gerencia tentativas e erros
                         │
                         └──> 3. END (End.py)
                              └─> Fecha conexões
                              └─> Gera relatórios finais
```

## 🔄 Fluxo de Dados

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Steam API   │      │   ITAD API   │      │  PostgreSQL  │
│              │      │              │      │              │
│ • Detalhes   │      │ • Histórico  │      │ • Raw Data   │
│ • Reviews    │      │   de Preços  │      │ • Processed  │
│ • Preços     │      │ • Promoções  │      │ • Analytics  │
└──────┬───────┘      └──────┬───────┘      └──────▲───────┘
       │                     │                      │
       │                     │                      │
       └──────────┬──────────┘                      │
                  │                                 │
                  ▼                                 │
         ┌────────────────┐                         │
         │   Previsor     │                         │
         │  (previsor.py) │                         │
         │                │                         │
         │ • Coleta       │─────────────────────────┘
         │ • Processa     │
         │ • Valida       │
         └────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Limpeza Dados  │
         │(limpeza_dados) │
         │                │
         │ • Normaliza    │
         │ • Valida       │
         │ • Transforma   │
         └────────────────┘
```

## 🗂️ Estrutura de Componentes

### **Framework** (Camada de Controle)
```
framework/
├── bot.py                  # Ponto de entrada principal
├── Initialization.py       # Setup inicial do sistema
├── Loop.py                 # Gerenciador do loop principal
├── Process.py              # Executor de tarefas
├── End.py                  # Encerramento e cleanup
└── AllSettings.py          # Configurações centralizadas
```

### **API** (Camada de Integração)
```
api/
├── steam_api.py            # Cliente Steam Web API
└── steam_appid_lookup.py   # Busca de IDs de jogos
```

### **SQL** (Camada de Persistência)
```
SQL/
├── postgre.py              # Gerenciador PostgreSQL
│   ├── Consultas otimizadas
│   ├── Inserções em lote
│   ├── Busca de AppIDs
│   └── Atualização de dados
└── supabase_db.py          # Integração Supabase (opcional)
```

### **Scripts** (Camada de Lógica)
```
scripts/
└── previsor.py             # Lógica principal do sistema
    ├── seleciona_games()
    ├── selecionar_base_dadosSteamBD()
    ├── alimentar_banco_dados_raw()
    └── alimentar_banco_dados_ITAD_docker()
```

### **Limpeza** (Camada de Processamento)
```
limpeza/
└── limpeza_dados.py        # Tratamento de dados
    ├── Normalização de datas
    ├── Limpeza de strings
    └── Validação de tipos
```

### **Utils** (Utilitários)
```
utils/
├── GetTask.py              # Gerenciamento de fila
├── buscar_appid.py         # Busca de IDs específicos
├── analisar_jogos_sem_reviews.py
├── validar_configuracao.py
└── migrar_dados_para_nuvem.py
```

## 🔀 Fluxo de Execução Detalhado

### 1. **Inicialização**
```python
Bot.start()
  ├─> Initialization.execute()
  │   ├─> Carrega Settings
  │   ├─> Conecta PostgreSQL
  │   ├─> Inicializa SteamClient
  │   └─> Valida configuração
```

### 2. **Loop Principal**
```python
Loop.execute()
  ├─> GetTask.load_task_queue()
  ├─> while tarefas_pendentes:
  │   ├─> Process.execute()
  │   │   └─> Previsor.alimentar_banco_dados_raw()
  │   │       ├─> SteamClient.buscar_detalhes()
  │   │       ├─> SteamClient.buscar_reviews()
  │   │       ├─> LimpezaDados.processar()
  │   │       └─> PostgreSQL.inserir_bulk()
  │   └─> Atualiza fila
```

### 3. **Processamento de Dados**
```python
Previsor.alimentar_banco_dados_raw()
  ├─> 1. Busca lista de AppIDs
  │       └─> PostgreSQL.buscar_appids_sem_dados()
  ├─> 2. Para cada batch de AppIDs:
  │       ├─> SteamClient.buscar_detalhes_async()
  │       ├─> SteamClient.buscar_reviews_async()
  │       └─> Aplica delays (rate limiting)
  ├─> 3. Filtra jogos relevantes
  │       └─> Previsor.seleciona_games()
  ├─> 4. Limpa e normaliza
  │       └─> LimpezaDados.processar()
  └─> 5. Insere no PostgreSQL
          └─> PostgreSQL.inserir_dados_bulk()
```

### 4. **Coleta de Dados ITAD**
```python
Previsor.alimentar_banco_dados_ITAD_docker()
  ├─> 1. Busca AppIDs sem ITAD
  │       └─> PostgreSQL.buscar_appids_sem_itad()
  ├─> 2. Para cada AppID:
  │       └─> ITAD_API.buscar_historico()
  ├─> 3. Processa em lotes
  │       └─> PostgreSQL.inserir_dados_itad_raw_batched()
  └─> 4. Atualiza timestamp
```

## 🎯 Padrões de Design Utilizados

### **1. Singleton Pattern**
- `Settings`: Uma única instância de configuração para todo o sistema

### **2. Factory Pattern**
- `InitApplication`: Cria e configura objetos complexos (clientes de API, conexões)

### **3. Strategy Pattern**
- `PostgreSQL` vs `SupabaseDB`: Diferentes estratégias de persistência

### **4. Pipeline Pattern**
- Coleta → Processamento → Limpeza → Armazenamento

### **5. Retry Pattern**
- Loop com `max_tentativas` para resiliência

## 🗄️ Modelo de Dados (Simplificado)

```
PostgreSQL Tables:
├─ steam_games_raw
│  ├─ appid (PK)
│  ├─ nome
│  ├─ desenvolvedores
│  ├─ preco
│  ├─ review_score
│  ├─ data_coleta
│  └─ json_completo
│
├─ itad_historico_raw
│  ├─ id (PK)
│  ├─ appid (FK)
│  ├─ preco
│  ├─ loja
│  ├─ data_preco
│  └─ desconto
│
└─ steam_games_processed
   ├─ appid (PK)
   ├─ categorias (Array)
   ├─ generos (Array)
   ├─ classificacao_etaria
   └─ metricas_processadas
```

## 🔧 Configuração Multi-PC

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   PC 1      │        │   PC 2      │        │   PC 3      │
│ (ID=1)      │        │ (ID=2)      │        │ (ID=3)      │
│             │        │             │        │             │
│ AppIDs:     │        │ AppIDs:     │        │ AppIDs:     │
│ 1,4,7,10... │        │ 2,5,8,11... │        │ 3,6,9,12... │
└─────┬───────┘        └─────┬───────┘        └─────┬───────┘
      │                      │                      │
      └──────────────────────┼──────────────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │   PostgreSQL    │
                   │  (Centralizado) │
                   └─────────────────┘
```

Cada PC processa apenas AppIDs onde: `appid % total_pcs == pc_id`

## 📊 Monitoramento e Logs

```
resources/
├── logs/
│   ├── execucao_YYYY-MM-DD.log
│   ├── erros_YYYY-MM-DD.log
│   └── batch_stats_YYYY-MM-DD.log
└── relatorios/
    ├── resumo_coleta.json
    └── estatisticas.csv
```

## 🚀 Performance e Otimizações

1. **Requisições Assíncronas**: Múltiplas chamadas de API simultâneas
2. **Inserção em Lote**: Até 1000 registros por operação
3. **Cache de Configurações**: Settings carregados uma vez
4. **Connection Pooling**: Reutilização de conexões PostgreSQL
5. **Rate Limiting Inteligente**: Respeita limites das APIs
6. **Processamento Distribuído**: Multi-PC para grandes volumes

---

> **Documento Técnico de Arquitetura**  
> Previsor Steam - TCC Ciência da Computação
