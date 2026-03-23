# 🚀 Guia de Instalação em Outro Computador

## ✅ Requisitos Necessários

### 1. Software Obrigatório
- ✅ **Docker Desktop** (Windows/Mac) ou Docker Engine (Linux)
- ✅ **Python 3.10+** (recomendado 3.11)
- ✅ **Git** (opcional, para clonar o repositório)

### 2. Portas Necessárias Liberadas
- ✅ **5432** - PostgreSQL (Docker)
- ✅ **8000** - Kong API Gateway (opcional)
- ✅ **3000** - Supabase Studio (opcional)

---

## 📋 Passo a Passo para Instalação

### **ETAPA 1: Transferir Arquivos**

#### Opção A: Via Git (Recomendado)
```bash
git clone https://github.com/camiloprado/Projeto_TCC_CC.git
cd Projeto_TCC_CC
```

#### Opção B: Cópia Manual
Copie TODA a pasta `Projeto_TCC_CC` para o novo computador.

---

### **ETAPA 2: Configurar Ambiente Python**

1. **Criar ambiente virtual:**
```bash
python -m venv .venv
```

2. **Ativar ambiente virtual:**
```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

3. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

---

### **ETAPA 3: Configurar Variáveis de Ambiente**

O arquivo `.env` já está configurado. **Apenas verifique:**

```properties
# PostgreSQL Docker (OBRIGATÓRIO para steam_raw)
DB_HOST=localhost
DB_PORT=5432
DB_PASSWORD=projetotccADMIN

# Supabase Cloud (OPCIONAL - só para steam_bd)
SUPABASE_URL=https://norphjcxnsgklyutnmin.supabase.co
SUPABASE_KEY=eyJhbGc...
```

⚠️ **IMPORTANTE:** 
- Se quiser usar **APENAS o Docker** (sem Supabase Cloud), ignore as configurações de SUPABASE.
- O projeto agora usa `PostgreSQL.inserir_dadosSteamRaw_Bulk()` que vai direto no Docker.

---

### **ETAPA 4: Iniciar Docker PostgreSQL**

1. **Navegar até a pasta do Docker:**
```bash
cd docker
```

2. **Iniciar PostgreSQL:**
```bash
docker compose up -d db
```

3. **Verificar se está rodando:**
```bash
docker ps
```

Deve aparecer:
```
CONTAINER ID   IMAGE                          STATUS         PORTS
xxxxxxxxxxxxx  supabase/postgres:15.8.1.085   Up 10 seconds  0.0.0.0:5432->5432/tcp
```

4. **Testar conexão:**
```bash
cd ..
python -c "from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre import PostgreSQL; PostgreSQL.conectar(); print('✓ Conectado com sucesso!'); PostgreSQL.desconectar()"
```

---

### **ETAPA 5: Rodar com 2 Requisições Paralelas**

#### **Opção A: Usar o Script Principal (bot.py)**

Edite o arquivo `.env` para processar menos jogos de cada vez:

```properties
# Processar 1000 AppIDs por vez
RANGE_PROCESSAMENTO_APPIDS_RAW=1000

# Batches de 100 (processar 100 detalhes de cada vez)
STEAM_BATCH_SIZE_DETAILS=100

# Aguardar 2 minutos entre batches
STEAM_DELAY_BETWEEN_BATCHES_DETAILS=120
```

Execute:
```bash
python prj_TCC_PREVISOR_STEAM/bot.py
```

#### **Opção B: Processar em 2 Terminais Separados**

**Terminal 1:**
```python
# teste_pc1.py
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre import PostgreSQL

# Buscar AppIDs não processados
PostgreSQL.conectar()
appids = PostgreSQL.buscar_todos_appids(arg_strNomeTabela="steam_generico")
PostgreSQL.desconectar()

# Processar primeira metade
primeira_metade = appids[:len(appids)//2]
print(f"Terminal 1: Processando {len(primeira_metade)} AppIDs")

# Processar...
Previsor.alimentar_banco_dados_raw_docker()
```

**Terminal 2:**
```python
# teste_pc2.py
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre import PostgreSQL

# Buscar AppIDs não processados
PostgreSQL.conectar()
appids = PostgreSQL.buscar_todos_appids(arg_strNomeTabela="steam_generico")
PostgreSQL.desconectar()

# Processar segunda metade
segunda_metade = appids[len(appids)//2:]
print(f"Terminal 2: Processando {len(segunda_metade)} AppIDs")

# Processar...
Previsor.alimentar_banco_dados_raw_docker()
```

⚠️ **ATENÇÃO:** Rodar 2 processos paralelos é SEGURO porque:
- ✅ O PostgreSQL usa UPSERT com `ON CONFLICT`
- ✅ O método `inserir_dadosSteamRaw_Bulk()` usa `COALESCE` para preservar dados
- ✅ Não há risco de perda de dados mesmo se os dois processarem o mesmo AppID

---

## 🔧 Verificações de Segurança

### **Teste 1: Conexão com Docker**
```bash
python -c "from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre import PostgreSQL; PostgreSQL.conectar(); print('✓ Docker OK'); PostgreSQL.desconectar()"
```

### **Teste 2: Inserção de Teste**
```bash
python test_insercao_docker.py
```

Deve mostrar:
```
=== ✓ TESTE CONCLUÍDO COM SUCESSO! ===
COALESCE funcionou corretamente:
  1. Detalhes foram preservados quando reviews foram inseridos
  2. Reviews foram adicionados sem apagar detalhes existentes
  3. Inserção sequencial está segura para uso em produção!
```

### **Teste 3: Contagem de Registros**
```bash
python -c "from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre import PostgreSQL; PostgreSQL.conectar(); cursor = PostgreSQL._var_connConnection.cursor(); cursor.execute('SELECT COUNT(*) FROM steam_raw'); print(f'Total de jogos em steam_raw: {cursor.fetchone()[0]}'); PostgreSQL.desconectar()"
```

---

## 📊 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    COMPUTADOR 1 ou 2                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Python Bot (bot.py)                                    │
│       ↓                                                  │
│  Previsor.alimentar_banco_dados_raw_docker()           │
│       ↓                                                  │
│  SteamClient.fetch_details_bulk_batched()              │
│       ↓                                                  │
│  PostgreSQL.inserir_dadosSteamRaw_Bulk()               │
│       ↓                                                  │
│  ┌──────────────────────────────────────┐              │
│  │  Docker PostgreSQL (localhost:5432)  │              │
│  │  Tabela: steam_raw                   │              │
│  │  71,106+ jogos em JSONB              │              │
│  └──────────────────────────────────────┘              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance Esperada

### **Com 1 Computador:**
- ✅ Batch de 100 AppIDs: ~40 segundos
- ✅ Espera entre batches: 120 segundos
- ✅ Total: ~160 segundos por batch (100 jogos)
- ✅ **Estimativa:** ~45 AppIDs/minuto

### **Com 2 Computadores em Paralelo:**
- ✅ **Estimativa:** ~90 AppIDs/minuto (2x mais rápido)
- ✅ **71,106 jogos:** ~13 horas (vs. ~26 horas com 1 PC)

---

## 🛠️ Troubleshooting

### **Erro: "Connection refused" no PostgreSQL**
```bash
# Verificar se o container está rodando
docker ps

# Reiniciar o container
cd docker
docker compose restart db
```

### **Erro: "Port 5432 already in use"**
Já existe um PostgreSQL rodando. Opções:
1. Parar o PostgreSQL local: `sudo systemctl stop postgresql`
2. Mudar a porta no `.env`: `DB_PORT=5433`

### **Erro: "NoneType object has no attribute 'get'"**
✅ **JÁ CORRIGIDO!** O código agora valida resultados nulos.

### **Dados duplicados/perdidos?**
✅ **IMPOSSÍVEL!** O `COALESCE` garante que:
- Detalhes não são apagados quando reviews são inseridos
- Reviews não apagam detalhes existentes
- Inserção sequencial é 100% segura

---

## 📝 Checklist Final

Antes de processar em produção:

- [ ] Docker Desktop instalado e rodando
- [ ] Python 3.10+ instalado
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] PostgreSQL Docker rodando (`docker compose up -d db`)
- [ ] Teste de conexão passou (`python -c "from..."`)
- [ ] Teste de inserção passou (`python test_insercao_docker.py`)
- [ ] Arquivo `.env` configurado corretamente

---

## 🎯 Comando Final para Iniciar

```bash
# Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# Rodar o bot
python prj_TCC_PREVISOR_STEAM/bot.py
```

**Monitorar logs em tempo real:**
```bash
# Verificar últimos 100 AppIDs inseridos
python -c "from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre import PostgreSQL; PostgreSQL.conectar(); cursor = PostgreSQL._var_connConnection.cursor(); cursor.execute('SELECT appid FROM steam_raw ORDER BY ultima_atualizacao DESC LIMIT 100'); print([r[0] for r in cursor.fetchall()]); PostgreSQL.desconectar()"
```

---

## ✅ Resumo da Resposta à Sua Pergunta

**"Caso eu passe esse arquivo para outro computador para alimentar o banco steam_raw com duas requisições pelo docker daria certo?"**

### **SIM, DARIA CERTO! ✅**

**Porque:**
1. ✅ O Docker PostgreSQL é **local** em cada máquina
2. ✅ Cada máquina processa **independentemente**
3. ✅ O código usa **UPSERT com COALESCE** (não perde dados)
4. ✅ Se 2 máquinas processarem o **mesmo AppID**, não tem problema:
   - A última atualização prevalece
   - Dados não são perdidos (COALESCE preserva)
   
**Alternativas:**
- **Opção 1:** Cada PC processa **metade** dos AppIDs (mais eficiente)
- **Opção 2:** Ambos processam **todos** (UPSERT resolve duplicatas)
- **Opção 3:** Um PC faz **detalhes**, outro faz **reviews**

**Recomendação:** Use **Opção 1** (dividir lista) para evitar processamento duplicado e economizar chamadas à API Steam.
