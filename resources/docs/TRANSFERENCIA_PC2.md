# ✅ Checklist de Transferência para o PC 2

## 📦 O Que Transferir

### **Arquivos do Projeto:**
```
Projeto_TCC_CC/
├── .env.pc2.example          # ⚠️ Copiar como .env no PC 2
├── docker-compose.yml
├── requirements.txt
├── setup.py
├── prj_TCC_PREVISOR_STEAM/   # Todo o código
├── CONFIGURACAO_MULTI_PC.md
└── OTIMIZACAO_CONSULTAS_SQL.md
```

---

## 🔧 Configuração do PC 2

### **1. Instalar Dependências**

```bash
# Docker Desktop
# Python 3.10+
# Git (opcional)

# Clonar/copiar projeto
cd D:\  # ou C:\
# Copiar pasta Projeto_TCC_CC

# Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar pacotes
pip install -r requirements.txt
```

---

### **2. Configurar .env do PC 2**

```bash
# No PC 2, copie o arquivo de exemplo
cp .env.pc2.example .env
```

**Arquivo `.env` do PC 2 deve ter:**
```env
# ⚠️ CONFIGURAÇÃO MULTI-PC - PC 2
PC_ID=2          # ← Este é o PC 2
TOTAL_PCS=2      # ← Total de 2 PCs

# ⚠️ MESMAS credenciais Supabase do PC 1
SUPABASE_URL=https://norphjcxnsgklyutnmin.supabase.co
SUPABASE_KEY=eyJhbGci...  # ← Mesma KEY do PC 1

# Docker PostgreSQL (local em cada PC)
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=projetotccADMIN
DB_HOST=localhost
DB_PORT=5432

# Ambiente
AMBIENTE=PRD
RANGE_PROCESSAMENTO_APPIDS_RAW=1000
```

---

### **3. Iniciar Docker PostgreSQL**

```bash
# No PC 2
docker-compose up -d

# Verificar se está rodando
docker ps

# Deve mostrar:
# CONTAINER ID   IMAGE         PORTS
# xxxxx          postgres:15   0.0.0.0:5432->5432/tcp
```

---

### **4. Criar Tabelas no PostgreSQL do PC 2**

O bot vai criar automaticamente quando executar pela primeira vez. Mas você pode criar manualmente:

```bash
# Conectar no PostgreSQL
docker exec -it <container_id> psql -U postgres

# Criar tabelas
CREATE TABLE IF NOT EXISTS steam_generico (
    id SERIAL PRIMARY KEY,
    appid INTEGER UNIQUE NOT NULL,
    name VARCHAR(500),
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS steam_raw (
    id SERIAL PRIMARY KEY,
    appid INTEGER UNIQUE NOT NULL,
    detalhes JSONB,
    reviews JSONB,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Sair
\q
```

---

### **5. Popular Tabela `steam_generico` (Importante!)**

⚠️ **Ambos os PCs precisam ter os mesmos AppIDs em `steam_generico`**

**Opção A: Copiar do PC 1**
```bash
# No PC 1, exportar
docker exec postgres pg_dump -U postgres -t steam_generico postgres > steam_generico.sql

# Copiar arquivo para PC 2 (USB, rede, etc.)

# No PC 2, importar
docker exec -i postgres psql -U postgres postgres < steam_generico.sql
```

**Opção B: Executar coleta da lista Steam**
```python
# No PC 2, rodar uma vez para popular steam_generico
# O bot vai baixar a lista da Steam API automaticamente
python prj_TCC_PREVISOR_STEAM/bot.py
```

---

## 🚀 Executar Bot no PC 2

### **Teste Inicial (Modo HML):**

```bash
# No .env do PC 2, configure:
AMBIENTE=HML
BATCH_TESTE=10

# Execute
python prj_TCC_PREVISOR_STEAM/bot.py
```

**Logs esperados:**
```
============================================================
MODO MULTI-PC ATIVADO: PC 2 de 2
============================================================
Consultando AppIDs não processados...
🔍 Buscando AppIDs não processados (PC 2/2)...
✅ Encontrados X AppIDs não processados para PC 2
```

---

### **Produção (Modo PRD):**

```bash
# No .env do PC 2:
AMBIENTE=PRD

# Execute
python prj_TCC_PREVISOR_STEAM/bot.py
```

---

## ✅ Validação - Como Saber se Está Funcionando

### **1. Verificar Divisão de Trabalho**

**PC 1 processa AppIDs PARES:**
```
AppIDs: 10, 20, 30, 40, 50...
```

**PC 2 processa AppIDs ÍMPARES:**
```
AppIDs: 11, 21, 31, 41, 51...
```

### **2. Verificar Logs**

**PC 1:**
```
INFO - MODO MULTI-PC ATIVADO: PC 1 de 2
INFO - ✅ Encontrados 35,000 AppIDs não processados para PC 1
```

**PC 2:**
```
INFO - MODO MULTI-PC ATIVADO: PC 2 de 2
INFO - ✅ Encontrados 35,000 AppIDs não processados para PC 2
```

### **3. Verificar Supabase**

Acesse o Supabase Dashboard e confirme:
- Dados de **ambos** os PCs estão sendo inseridos
- Não há duplicação de AppIDs
- Tabelas: `steam_bd`, `steam_generico`

### **4. Verificar PostgreSQL Local (Docker)**

```bash
# No PC 2, verificar quantos registros foram inseridos
docker exec -it postgres psql -U postgres -c "SELECT COUNT(*) FROM steam_raw;"

# Ver alguns registros
docker exec -it postgres psql -U postgres -c "SELECT appid FROM steam_raw LIMIT 10;"
```

---

## ⚠️ Problemas Comuns

### **1. "Nenhum AppID para processar"**
```
✅ Nenhum AppID para processar! Todos os dados estão atualizados.
```

**Solução:** 
- Verifique se `steam_generico` está populado
- Confirme que `PC_ID` e `TOTAL_PCS` estão corretos no `.env`

---

### **2. "AppIDs duplicados no Supabase"**
**Causa:** Ambos os PCs com `PC_ID=1` ou `TOTAL_PCS` diferente

**Solução:**
```env
# PC 1: .env
PC_ID=1
TOTAL_PCS=2

# PC 2: .env
PC_ID=2
TOTAL_PCS=2
```

---

### **3. "Erro ao conectar PostgreSQL"**
```
Erro ao conectar ao banco de dados: Connection refused
```

**Solução:**
```bash
# Verificar se Docker está rodando
docker ps

# Se não estiver, inicie
docker-compose up -d

# Verificar logs
docker-compose logs db
```

---

### **4. "Timeout ao buscar AppIDs"**
**Solução:** Já resolvido com otimizações SQL! ✅
- Consultas agora usam LEFT JOIN eficiente
- Não carregam 280k registros na memória

---

## 📊 Monitoramento em Tempo Real

### **Ver progresso do PC 2:**
```bash
# Terminal 1: Executar bot
python prj_TCC_PREVISOR_STEAM/bot.py

# Terminal 2: Monitorar logs
tail -f logs/bot_*.log | grep "Progresso:"
```

### **Comparar com PC 1:**
Execute o mesmo comando em ambos os PCs e compare os AppIDs sendo processados.

---

## 🎯 Resultado Esperado

### **Com 2 PCs Trabalhando:**

| Métrica | 1 PC | 2 PCs | Melhoria |
|---------|------|-------|----------|
| **AppIDs/min** | ~45 | ~90 | **2x mais rápido** |
| **Tempo total (71k jogos)** | ~26h | ~13h | **50% mais rápido** |
| **Carga por PC** | 100% | 50% | **Melhor distribuição** |

---

## 🔒 Garantias de Segurança

### **Dados Locais (Docker PostgreSQL):**
- ✅ Cada PC tem seu próprio banco local
- ✅ Usado apenas como cache temporário
- ✅ Não há comunicação entre os PCs via Docker

### **Dados Centralizados (Supabase):**
- ✅ Ambos os PCs gravam no **mesmo Supabase**
- ✅ Sem duplicação (divisão por MOD no SQL)
- ✅ Dados persistentes e acessíveis de qualquer lugar

### **Divisão de Trabalho:**
- ✅ PC 1: AppIDs com `MOD(appid, 2) = 0` (pares)
- ✅ PC 2: AppIDs com `MOD(appid, 2) = 1` (ímpares)
- ✅ Sem conflito ou duplicação

---

## ✅ Checklist Final

### **No PC 2:**
- [ ] Docker instalado e rodando
- [ ] Python 3.10+ instalado
- [ ] Projeto copiado/clonado
- [ ] `.venv` criado e ativado
- [ ] `requirements.txt` instalado
- [ ] `.env` configurado com `PC_ID=2` e `TOTAL_PCS=2`
- [ ] Credenciais Supabase **iguais** ao PC 1
- [ ] `docker-compose up -d` executado
- [ ] Container PostgreSQL rodando
- [ ] Tabela `steam_generico` populada (mesma do PC 1)
- [ ] Teste em modo HML executado com sucesso

### **Validação:**
- [ ] Logs mostram "PC 2 de 2"
- [ ] AppIDs processados são diferentes do PC 1
- [ ] Dados aparecendo no Supabase
- [ ] Sem erros de duplicação

---

## 🚀 Comando Final

```bash
# No PC 2 (após toda configuração)
cd D:\Projeto_TCC_CC  # ou caminho do projeto
.venv\Scripts\activate
python prj_TCC_PREVISOR_STEAM/bot.py
```

**Pronto!** Os 2 PCs vão trabalhar em paralelo coletando dados da Steam! 🎉

---

## 📞 Suporte Rápido

### **Verificar estado do sistema:**
```bash
# Docker
docker ps

# Banco local
docker exec postgres psql -U postgres -c "SELECT COUNT(*) FROM steam_raw;"

# Python
python --version

# Ambiente virtual
which python  # Linux/Mac
where python  # Windows
```

### **Logs importantes:**
```bash
# Logs do bot
tail -f logs/bot_*.log

# Logs do Docker
docker-compose logs db

# Erros Python
python prj_TCC_PREVISOR_STEAM/bot.py 2>&1 | tee debug.log
```

---

**Está tudo pronto para rodar no PC 2!** 🚀
