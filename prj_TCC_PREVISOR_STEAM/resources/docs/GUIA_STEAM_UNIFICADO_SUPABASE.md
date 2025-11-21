# 🚀 Guia: Subir steam_unificado para o Supabase

## 📋 Pré-requisitos

1. ✅ Tabela `steam_unificado` no Docker PostgreSQL (já criada - 173.843 registros)
2. ⚙️ Credenciais Supabase no `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

---

## 🔧 Passo 1: Criar Tabela no Supabase

### Opção A: Via Supabase Dashboard (Recomendado)
1. Acesse: https://supabase.com/dashboard
2. Selecione seu projeto
3. Vá em: **SQL Editor**
4. Copie e cole o conteúdo de: `resources/docs/create_steam_unificado_supabase.sql`
5. Clique em **Run**

### Opção B: Via Terminal (se tiver acesso direto)
```bash
# Conecte ao PostgreSQL do Supabase e execute o SQL
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres" < resources/docs/create_steam_unificado_supabase.sql
```

---

## 📤 Passo 2: Sincronizar Dados

### Teste com 1.000 registros primeiro:
```bash
python sync_steam_unificado_supabase.py 500 1000
```
- Argumento 1: Batch size (500)
- Argumento 2: Limite de registros (1000 para teste)

### Sincronizar TODOS os registros (173.843):
```bash
python sync_steam_unificado_supabase.py 500
```

**Tempo estimado:** 
- 1.000 registros: ~2-3 minutos
- 173.843 registros: ~60-90 minutos

---

## 🔍 Passo 3: Verificar Sincronização

### Via Python:
```python
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

# Conectar
SupabaseDB.conectar()

# Verificar total
total = SupabaseDB.contar_steam_unificado()
print(f"Total no Supabase: {total:,}")

# Buscar um jogo
jogo = SupabaseDB.buscar_steam_unificado(10)
print(f"Counter-Strike: {jogo['nome']}")
```

### Via Supabase Dashboard:
1. Acesse: **Table Editor**
2. Selecione: `steam_unificado`
3. Verifique os dados

---

## 📊 Métodos Disponíveis

### SupabaseDB (Cloud):
```python
# Inserir/atualizar um registro
SupabaseDB.inserir_steam_unificado(dados)

# Inserir/atualizar em lote
SupabaseDB.inserir_steam_unificado_bulk(lista_dados)

# Buscar por AppID
jogo = SupabaseDB.buscar_steam_unificado(appid)

# Buscar todos (com paginação)
jogos = SupabaseDB.buscar_todos_steam_unificado(limit=100, offset=0)

# Contar registros
total = SupabaseDB.contar_steam_unificado()
```

### PostgreSQL (Docker Local):
```python
# Inserir/atualizar um registro
PostgreSQL.inserir_steam_unificado(dados)

# Buscar por AppID
jogo = PostgreSQL.buscar_steam_unificado(appid)

# Buscar todos
jogos = PostgreSQL.buscar_todos_steam_unificado(limit=100)
```

---

## ⚡ Uso Automático

### Modificar ProcessadorETL para usar ambos:
```python
# Inserir no Docker E no Supabase
PostgreSQL.inserir_steam_unificado(dados)
SupabaseDB.inserir_steam_unificado(dados)
```

---

## 🚨 Troubleshooting

### Erro: "relation steam_unificado does not exist"
**Solução:** Execute o SQL no Supabase Dashboard primeiro (Passo 1)

### Erro: "Row Level Security policy violation"
**Solução:** Verifique se as políticas RLS foram criadas corretamente no SQL

### Erro: Rate limiting
**Solução:** Reduza o batch size: `python sync_steam_unificado_supabase.py 250`

### Sincronização lenta
**Solução:** Aumente o batch size (cuidado com rate limits): `python sync_steam_unificado_supabase.py 1000`

---

## 📈 Monitoramento

Durante a sincronização, você verá:
```
2025-11-19 14:30:15 - INFO - Docker: 173,843 registros
2025-11-19 14:30:15 - INFO - Supabase: 0 registros
2025-11-19 14:30:20 - INFO - Processando registros 1 a 500 de 173,843...
2025-11-19 14:30:25 - INFO - ✓ Batch inserido com sucesso (500/173,843)
...
```

---

## ✅ Checklist Final

- [ ] Criar tabela no Supabase (SQL)
- [ ] Verificar credenciais no `.env`
- [ ] Testar com 1.000 registros
- [ ] Sincronizar todos os registros
- [ ] Verificar total no Supabase
- [ ] Testar queries via SupabaseDB
- [ ] Atualizar código para usar Supabase

---

**Arquivos criados:**
- `resources/docs/create_steam_unificado_supabase.sql` - SQL para criar tabela
- `sync_steam_unificado_supabase.py` - Script de sincronização
- Métodos em `supabase_db.py` - Interface Python

**Próximo passo:** Execute o Passo 1 (criar tabela no Supabase)! 🚀
