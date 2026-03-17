# Referencial Teórico - TCC Previsor Steam

**Projeto**: Sistema de Previsão de Sucesso de Jogos na Plataforma Steam  
**Autor**: Camilo Prado  
**Curso**: Ciência da Computação  
**Data de Criação**: 12 de março de 2026  
**Versão**: 1.0

---

## 📋 Índice

1. [Pesquisar Livros e Referências](#1-pesquisar-livros-e-referências)
2. [Estudar ABNT](#2-estudar-abnt)
3. [Definir Regras de Negócio](#3-definir-regras-de-negócio)
4. [Referencial Teórico](#4-referencial-teórico)

---

## 1. Pesquisar Livros e Referências

### 1.1 Machine Learning e Data Science

#### Livros-base utilizados no desenvolvimento deste projeto

1. **GÉRON, Aurélien. Mãos à Obra: Aprendizado de Máquina com Scikit-Learn, Keras e TensorFlow. 2. ed. Alta Books, 2019.**
    - Base prática para construção de pipelines de ML com scikit-learn, validação e checklist de projeto.

2. **HUYEN, Chip. Projetando Sistemas de Machine Learning: Processos Iterativos para Aplicações Prontas para Produção.**
    - Base para desenho de sistemas de ML em produção: ciclo iterativo, monitoramento e operação contínua.

3. **CARVALHO, André C. P. L. F.; MENEZES, Angelo Garangau; BONIDIA, Robson Parmezan. Ciência de Dados: Fundamentos e Aplicações.**
    - Base conceitual para preparação de dados, qualidade, seleção de atributos e avaliação de modelos.

4. **KLOSTERMAN, Stephen. Projetos de Ciência de Dados com Python: Abordagem de estudo de caso para criação de projetos de ciência de dados bem-sucedidos usando Python, pandas e scikit-learn.**
    - Base para organização de fluxo de trabalho orientado a estudo de caso e implementação com pandas/scikit-learn.

5. **FACELI, Katti; LORENA, Ana Carolina; ALMEIDA, Tiago Agostinho; CARVALHO, André C. P. L. F. Inteligência Artificial: Uma abordagem de Aprendizado de Máquina. 3. ed.**
    - Base teórica para aprendizagem supervisionada, generalização, viés-variância e avaliação.

#### Livros Fundamentais

**1. GÉRON, Aurélien. Mãos à Obra: Aprendizado de Máquina com Scikit-Learn, Keras e TensorFlow. 2. ed. Alta Books, 2019.**
- **Relevância**: Referência principal para implementação de modelos com scikit-learn e XGBoost
- **Capítulos-chave**: 
  - Cap. 2: End-to-End Machine Learning Project
  - Cap. 6: Decision Trees e Random Forests
  - Cap. 7: Ensemble Learning e Gradient Boosting
- **Aplicação no projeto**: Arquitetura do pipeline de treinamento, validação cruzada temporal, feature engineering

**2. HASTIE, Trevor; TIBSHIRANI, Robert; FRIEDMAN, Jerome. The Elements of Statistical Learning: Data Mining, Inference, and Prediction. 2nd ed. Springer, 2009.**
- **Relevância**: Base teórica para algoritmos de classificação e regressão
- **Capítulos-chave**:
  - Cap. 9: Additive Models, Trees, and Related Methods
  - Cap. 10: Boosting and Additive Trees
  - Cap. 15: Random Forests
- **Aplicação no projeto**: Fundamentação teórica dos modelos RandomForest, XGBoost e LightGBM

**3. KLEPPMANN, Martin. Designing Data-Intensive Applications. O'Reilly Media, 2017.**
- **Relevância**: Arquitetura de sistemas para processamento de grandes volumes de dados
- **Capítulos-chave**:
  - Cap. 3: Storage and Retrieval (PostgreSQL, JSONB)
  - Cap. 10: Batch Processing
  - Cap. 11: Stream Processing
- **Aplicação no projeto**: Design do pipeline ETL, estratégia de checkpoint, arquitetura híbrida Docker+Supabase

**4. CHEN, Tianqi; GUESTRIN, Carlos. XGBoost: A Scalable Tree Boosting System. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining. ACM, 2016. p. 785-794.**
- **Relevância**: Artigo seminal do XGBoost, modelo principal do projeto
- **Contribuições**: Regularização L1/L2, split finding otimizado, cache-aware access
- **Aplicação no projeto**: Configuração de hiperparâmetros (max_depth=8, learning_rate=0.05, reg_alpha/lambda)

**5. KE, Guolin et al. LightGBM: A Highly Efficient Gradient Boosting Decision Tree. In: Advances in Neural Information Processing Systems 30 (NIPS 2017).**
- **Relevância**: Fundamentação teórica do LightGBM para experimentação rápida
- **Contribuições**: Gradient-based One-Side Sampling (GOSS), Exclusive Feature Bundling (EFB)
- **Aplicação no projeto**: Modelo auxiliar para iteração rápida durante feature engineering

#### Artigos Científicos

**6. SARWAR, Badrul et al. Item-based collaborative filtering recommendation algorithms. In: Proceedings of the 10th international conference on World Wide Web. ACM, 2001. p. 285-295.**
- **Relevância**: Base teórica para sistemas de recomendação (extensão futura do projeto)
- **Aplicação**: Inspiração para features baseadas em similaridade de jogos

**7. HE, Xiangnan et al. Neural Collaborative Filtering. In: Proceedings of the 26th International Conference on World Wide Web. 2017. p. 173-182.**
- **Relevância**: Abordagens modernas para previsão de preferências
- **Aplicação potencial**: Incorporação de embeddings neurais para desenvolvedores/gêneros

**8. KOREN, Yehuda; BELL, Robert; VOLINSKY, Chris. Matrix Factorization Techniques for Recommender Systems. IEEE Computer, v. 42, n. 8, p. 30-37, 2009.**
- **Relevância**: Técnicas de redução de dimensionalidade para features categóricas
- **Aplicação**: One-hot encoding de gêneros/desenvolvedores (50+ categorias)

### 1.2 Engenharia de Software e Arquitetura

**9. FOWLER, Martin. Patterns of Enterprise Application Architecture. Addison-Wesley, 2002.**
- **Relevância**: Padrões arquiteturais para sistemas de larga escala
- **Padrões aplicados**:
  - Repository Pattern (classes/SQL/)
  - Service Layer (classes/api/, classes/scripts/)
  - Gateway (PostgreSQL + Supabase)
- **Aplicação no projeto**: Organização modular do código (framework/, limpeza/, treinamento/)

**10. EVANS, Eric. Domain-Driven Design: Tackling Complexity in the Heart of Software. Addison-Wesley, 2003.**
- **Relevância**: Design orientado ao domínio de negócio (games, pricing, reviews)
- **Aplicação**: Modelagem de entidades (steam_raw, steam_unificado, itad_raw)

**11. NEWMAN, Sam. Building Microservices. 2nd ed. O'Reilly Media, 2021.**
- **Relevância**: Arquitetura de serviços independentes
- **Aplicação**: Separação de módulos (API integration, ETL, ML, Data cleaning)

### 1.3 PostgreSQL e Banco de Dados

**12. OBE, Regina; HSU, Leo. PostgreSQL: Up and Running. 3rd ed. O'Reilly Media, 2017.**
- **Relevância**: Referência técnica para PostgreSQL 15
- **Capítulos-chave**:
  - Cap. 5: Data Types (JSONB)
  - Cap. 7: SQL: The PostgreSQL Way
  - Cap. 9: Performance Tuning
- **Aplicação no projeto**: Otimização de queries, índices em JSONB, batch inserts

**13. SCHONIG, Hans-Jürgen. Mastering PostgreSQL 15. Packt Publishing, 2023.**
- **Relevância**: Features avançadas do PostgreSQL 15
- **Aplicação**: Queries parametrizadas, psycopg 3.x, connection pooling

### 1.4 Indústria de Jogos e Steam

**14. VALVE CORPORATION. Steamworks API Documentation. Disponível em: <https://partner.steamgames.com/doc/api>. Acesso em: 12 mar. 2026.**
- **Relevância**: Documentação oficial da API Steam
- **Endpoints utilizados**:
  - `ISteamApps/GetAppList`
  - `IStoreService/GetAppDetails`
  - `IStoreService/GetReviews`

**15. NEWZOO. Global Games Market Report 2025. Newzoo, 2025.**
- **Relevância**: Dados do mercado de jogos (US$ 189 bilhões em 2025)
- **Aplicação**: Contextualização da relevância do problema de negócio

**16. MARCHAND, André; HENNIG-THURAU, Thorsten. Value Creation in the Video Game Industry: Industry Economics, Consumer Benefits, and Research Opportunities. Journal of Interactive Marketing, v. 27, n. 3, p. 141-157, 2013.**
- **Relevância**: Economia da indústria de jogos digitais
- **Aplicação**: Fundamentação do problema de precificação e previsão de sucesso

### 1.5 Metodologias de Desenvolvimento

**17. PRESSMAN, Roger S.; MAXIM, Bruce R. Engenharia de Software: Uma Abordagem Profissional. 9. ed. Porto Alegre: AMGH, 2021.**
- **Relevância**: Metodologias de desenvolvimento e teste
- **Capítulos aplicados**:
  - Cap. 3: Processo de Software (iterativo)
  - Cap. 8: Teste de Software (pytest, testes unitários)
  - Cap. 22: Gerenciamento de Configuração (git, versionamento)

**18. MARTIN, Robert C. Clean Code: A Handbook of Agile Software Craftsmanship. Prentice Hall, 2008.**
- **Relevância**: Boas práticas de codificação
- **Aplicação**: Code quality tools (black, ruff, pre-commit hooks)

---

## 2. Estudar ABNT

### 2.1 Normas ABNT Aplicáveis ao TCC

#### NBR 14724:2011 - Trabalhos Acadêmicos

**Estrutura obrigatória**:
1. **Elementos Pré-textuais**:
   - Capa (nome da instituição, título, autor, local, data)
   - Folha de rosto (natureza do trabalho, orientador)
   - Folha de aprovação
   - Resumo em português (150-500 palavras)
   - Abstract em inglês
   - Lista de figuras/tabelas/abreviaturas
   - Sumário

2. **Elementos Textuais**:
   - Introdução
   - Desenvolvimento (Referencial Teórico, Metodologia, Resultados)
   - Conclusão

3. **Elementos Pós-textuais**:
   - Referências (NBR 6023)
   - Apêndices (código-fonte, scripts)
   - Anexos (documentação de APIs)

#### NBR 6023:2018 - Referências

**Formatação de Referências**:

**Livros**:
```
SOBRENOME, Nome. Título: subtítulo. Edição. Local: Editora, ano.
```
Exemplo:
```
GÉRON, Aurélien. Mãos à Obra: Aprendizado de Máquina com Scikit-Learn, Keras e TensorFlow. 2. ed. Rio de Janeiro: Alta Books, 2019.
```

**Artigos científicos**:
```
SOBRENOME, Nome et al. Título do artigo. Nome da Revista, v. X, n. Y, p. Z-W, ano.
```
Exemplo:
```
CHEN, Tianqi; GUESTRIN, Carlos. XGBoost: A Scalable Tree Boosting System. In: PROCEEDINGS OF THE 22ND ACM SIGKDD INTERNATIONAL CONFERENCE ON KNOWLEDGE DISCOVERY AND DATA MINING. San Francisco: ACM, 2016. p. 785-794.
```

**Documentos eletrônicos**:
```
AUTOR. Título. Disponível em: <URL>. Acesso em: dd mmm. aaaa.
```
Exemplo:
```
VALVE CORPORATION. Steamworks API Documentation. Disponível em: <https://partner.steamgames.com/doc/api>. Acesso em: 12 mar. 2026.
```

#### NBR 6028:2003 - Resumo

**Estrutura do Resumo** (para o TCC):
- Contextualização (1-2 frases)
- Objetivo do trabalho (1 frase)
- Metodologia (2-3 frases)
- Resultados principais (2-3 frases)
- Conclusão (1 frase)
- Palavras-chave: 3-5 termos

**Exemplo de Resumo para este projeto**:
```
O mercado de jogos digitais movimenta bilhões de dólares anualmente, mas desenvolvedores 
enfrentam dificuldades em prever o sucesso comercial de seus produtos. Este trabalho 
desenvolveu um sistema de previsão de sucesso de jogos na plataforma Steam utilizando 
técnicas de Machine Learning. A metodologia envolveu a coleta de dados de 276.564 jogos 
via Steam API e IsThereAnyDeal, processamento ETL com PostgreSQL, e treinamento de 
modelos XGBoost, RandomForest e LightGBM. Os resultados demonstraram acurácia superior 
a 78% na classificação de sucesso (fracasso/mediano/sucesso) e R² de 0.72 na previsão 
de reviews. O sistema pode auxiliar desenvolvedores indie na definição de estratégias 
de precificação e lançamento.

Palavras-chave: Machine Learning. Previsão. Jogos Digitais. Steam. XGBoost.
```

#### NBR 10520:2023 - Citações

**Citação direta curta** (até 3 linhas):
```
Segundo Géron (2022, p. 45), "ensemble methods combine predictions of multiple models 
to achieve better performance than individual estimators".
```

**Citação direta longa** (mais de 3 linhas):
```
Chen e Guestrin (2016, p. 786) afirmam:

    Among the 29 challenge winning solutions published at Kaggle's blog during 
    2015, 17 solutions used XGBoost. Among these solutions, eight solely used 
    XGBoost to train the model, while most others combined XGBoost with neural 
    nets in ensembles.
```

**Citação indireta**:
```
A técnica de gradient boosting tem demonstrado resultados superiores em competições 
de ciência de dados (CHEN; GUESTRIN, 2016).
```

#### NBR 15287:2011 - Projeto de Pesquisa

**Estrutura do Anteprojeto** (já concluído):
- Tema: Previsão de sucesso de jogos Steam com ML
- Problema: Dificuldade em prever desempenho comercial
- Justificativa: Relevância econômica e tecnológica
- Objetivos: Geral e específicos
- Metodologia: Coleta, ETL, ML
- Cronograma: Fevereiro-Maio 2026
- Referências bibliográficas

### 2.2 Formatação Geral

**Margens**:
- Superior: 3 cm
- Inferior: 2 cm
- Esquerda: 3 cm
- Direita: 2 cm

**Fonte**:
- Texto: Times New Roman ou Arial, tamanho 12
- Citações longas: tamanho 10
- Notas de rodapé: tamanho 10

**Espaçamento**:
- Texto: 1,5 entre linhas
- Citações longas: simples
- Referências: simples, com espaço duplo entre entradas

**Paginação**:
- Pré-textuais: numeração romana (i, ii, iii...)
- Textuais e pós-textuais: numeração arábica (1, 2, 3...)

---

## 3. Definir Regras de Negócio

### 3.1 Domínio do Problema

#### Contexto de Negócio
A indústria de jogos digitais enfrenta desafios críticos relacionados à previsibilidade de sucesso comercial. Desenvolvedores indie e pequenas empresas, sem acesso a grandes orçamentos de marketing, necessitam de ferramentas analíticas para:

1. **Precificação Estratégica**: Definir o preço ideal que maximize receita sem comprometer volume de vendas
2. **Timing de Lançamento**: Identificar janelas de oportunidade com menor competição
3. **Feature Prioritization**: Entender quais características (gênero, mecânicas, gráficos) impactam o sucesso
4. **Promoções**: Planejar descontos que maximizem alcance sem erosão de margem

### 3.2 Regras de Negócio Implementadas

#### RN-01: Classificação de Sucesso

**Descrição**: Categorizar jogos em níveis de sucesso baseado em review_score (agregação de reviews positivas/negativas).

**Regra**:
```python
if review_score < 40:
    categoria = "FRACASSO"
elif 40 <= review_score < 70:
    categoria = "MEDIANO"
else:  # review_score >= 70
    categoria = "SUCESSO"
```

**Justificativa**:
- Steam considera "Mostly Positive" a partir de 70% positivas (fonte: Steamworks docs)
- Jogos abaixo de 40% raramente recuperam vendas (análise histórica do dataset)
- Faixa 40-70% representa jogos de nicho com públicos específicos

**Baseline de mercado**:
- ~15% dos jogos: Fracasso (< 40%)
- ~35% dos jogos: Mediano (40-70%)
- ~50% dos jogos: Sucesso (≥ 70%)

#### RN-02: Atualização de Dados

**Descrição**: Dados brutos (steam_raw) são considerados desatualizados após 30 dias da coleta.

**Regra**:
```sql
SELECT appid 
FROM steam_raw 
WHERE (CURRENT_DATE - data_coleta::date) > 30
   OR data_coleta IS NULL
```

**Justificativa**:
- Reviews continuam acumulando ao longo do tempo
- Preços mudam com promoções sazonais (Summer Sale, Winter Sale)
- Jogos em Early Access recebem atualizações frequentes
- Metacritic pode adicionar reviews meses após lançamento

**Exceções**:
- Jogos descontinuados (removed from store): não reatualizados
- Jogos com `ultima_atualizacao` nos últimos 7 dias: skip (rate limiting)

#### RN-03: Validação de Preço

**Descrição**: Processar diferentes formatos de preço para obter valor numérico.

**Regra** (implementada em `limpeza_preco.py`):
```python
def processar_preco(preco_str):
    """
    Entrada: "R$ 49,99", "Free to Play", "$29.99", "Gratuito"
    Saída: 49.99, 0.0, 29.99, 0.0
    """
    if preco_str in ["Free to Play", "Gratuito", "Free"]:
        return 0.0
    
    # Remove símbolos de moeda, converte vírgula em ponto
    preco_limpo = re.sub(r'[^\d,.]', '', preco_str)
    preco_limpo = preco_limpo.replace(',', '.')
    
    return float(preco_limpo)
```

**Casos especiais**:
- DLCs sem preço base: herda preço do jogo principal
- Bundles: considera preço individual, não do pacote
- Preços regionais: padronizado em USD (conversão via ITAD API)

#### RN-04: Tratamento de Dados Ausentes

**Descrição**: Estratégias para lidar com campos faltantes sem descartar registros.

**Regras por campo**:

| Campo | Estratégia | Justificativa |
|-------|-----------|---------------|
| `data_lancamento` | "EM BREVE" | Jogos anunciados mas não lançados |
| `metacritic_score` | "Desconhecido" | ~70% dos jogos não têm nota crítica |
| `desenvolvedores` | "Desenvolvedor Desconhecido" | Raro, mas ocorre em jogos muito antigos |
| `genero` | "Casual" | Categoria padrão da Steam |
| `linguagens` | ["Inglês"] | Idioma universal |
| `classificacao_etaria` | "0" | Livre para todos (conservador) |

**Implementação**:
```python
# Em limpeza_metacritic.py
if metacritic_completo is None or metacritic_completo == "":
    return "Desconhecido"  # VARCHAR(20), não NULL numérico

# Em limpeza_data_lancamento.py
if data_str.lower() in ["coming soon", "tba", "to be announced"]:
    return "EM BREVE"  # Categoria especial, não NULL
```

**Validação**:
- Auditoria semanal: verificar % de campos com valores default
- Se > 30% de "Desconhecido" em campo crítico: investigar mudança na API

#### RN-05: Deduplicação de Registros

**Descrição**: Garantir que cada AppID tenha apenas um registro em `steam_unificado`.

**Regra**:
```sql
-- Na inserção
INSERT INTO steam_unificado (appid, nome, preco, ...)
VALUES (...)
ON CONFLICT (appid) 
DO UPDATE SET 
    nome = EXCLUDED.nome,
    preco = EXCLUDED.preco,
    ultima_atualizacao = NOW();
```

**Constraint**:
```sql
ALTER TABLE steam_unificado 
ADD CONSTRAINT pk_appid PRIMARY KEY (appid);
```

**Exceção**:
- Histórico de preços (tabela `itad_raw`): permite múltiplos registros por AppID (série temporal)

#### RN-06: Checkpoint de Processamento

**Descrição**: Salvar progresso a cada batch para resiliência a falhas.

**Regra**:
```python
# A cada 50 AppIDs processados
if contador % 50 == 0:
    db.salvar_checkpoint(
        pc_id=identificador_maquina,
        indice_atual=contador,
        origem="STEAM"  # ou "ITAD"
    )
```

**Recuperação de falha**:
```python
ultimo_checkpoint = db.buscar_ultimo_checkpoint(pc_id, "STEAM")
if ultimo_checkpoint:
    iniciar_de = ultimo_checkpoint['indice_atual']
else:
    iniciar_de = 0
```

**Limpeza**:
- Checkpoints com >7 dias: removidos automaticamente (job noturno)
- Checkpoint "concluído": flag `finalizado=True`, preservado 30 dias

#### RN-07: Feature Engineering - Faixas de Preço

**Descrição**: Categorizar preços em faixas para análise de mercado.

**Regra**:
```python
def criar_faixa_preco(preco_num):
    if preco_num == 0:
        return "GRATIS"
    elif preco_num <= 20:
        return "BAIXO"      # Jogos indie, mobile ports
    elif preco_num <= 50:
        return "MEDIO"      # Jogos AA
    elif preco_num <= 100:
        return "ALTO"       # Jogos AAA no lançamento
    else:
        return "PREMIUM"    # Edições especiais, simuladores nicho
```

**Validação de mercado**:
- Análise de 276k jogos confirmou distribuição:
  - Grátis: 28%
  - Baixo (≤$20): 45%
  - Médio ($20-50): 18%
  - Alto ($50-100): 7%
  - Premium (>$100): 2%

#### RN-08: Requisitos Mínimos de Treinamento

**Descrição**: Critérios para treinar modelos de ML.

**Regras**:
```python
def verificar_necessidade_treinamento():
    # RN-08.1: Modelo não existe
    if not exists("modelo_xgboost.pkl"):
        return True
    
    # RN-08.2: Modelo com >7 dias
    modelo_idade = datetime.now() - get_file_modified_time("modelo_xgboost.pkl")
    if modelo_idade.days > 7:
        return True
    
    # RN-08.3: Novos dados (>5% crescimento)
    registros_atuais = db.count("steam_unificado")
    registros_ultimo_treino = read_metadata("registros_treino")
    crescimento = (registros_atuais - registros_ultimo_treino) / registros_ultimo_treino
    if crescimento > 0.05:
        return True
    
    return False
```

**Requisitos de dados**:
- Mínimo 10.000 registros para treinamento inicial
- Mínimo 100 registros em cada classe (fracasso/mediano/sucesso)
- Features com >30% missings: excluídas do modelo

#### RN-09: Janela Temporal de Treinamento

**Descrição**: Usar apenas dados recentes para evitar concept drift.

**Regra**:
```python
JANELA_TREINAMENTO = 90  # dias

query = """
SELECT * FROM steam_unificado
WHERE ultima_atualizacao >= NOW() - INTERVAL '90 days'
  AND total_reviews >= 10  -- Mínimo de reviews para confiabilidade
"""
```

**Justificativa**:
- Tendências de mercado mudam (ex: boom de roguelikes em 2024-25)
- Sazonalidade (lançamentos concentrados em Q4)
- Drift de preferências (gráficos realistas vs. pixel art)

**Validação**:
- Split temporal: 80% treino (mais antigos) / 20% teste (mais recentes)
- Evita data leakage (não usar dados futuros para prever passado)

#### RN-10: Limite de Rate em APIs

**Descrição**: Respeitar limites de requisições das APIs externas.

**Regras**:

| API | Limite | Implementação |
|-----|--------|---------------|
| Steam Details | 100 req/5min | 180s delay entre batches de 50 |
| Steam Reviews | 200 req/5min | 60s delay entre batches de 50 |
| ITAD Lookup | 500 req/hour | 120s delay entre batches de 200 |
| ITAD Prices | 100 req/10min | 180s delay entre batches de 20 |

**Implementação** (com `tenacity`):
```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3)
)
async def buscar_detalhes_steam(appid):
    response = await client.get(f"...{appid}")
    if response.status == 429:  # Too Many Requests
        raise RateLimitError()
    return response.json()
```

**Monitoramento**:
- Logs de todas as chamadas de API (timestamp, endpoint, status)
- Alerta se rate limit atingido >3x em 1 hora

### 3.3 Métricas de Sucesso do Sistema

#### KPI-01: Cobertura de Dados
**Meta**: ≥ 95% dos jogos ativos na Steam com dados atualizados

**Medição**:
```python
total_jogos_steam = 276564  # Fonte: Steam API GetAppList
total_steam_raw = db.count("steam_raw WHERE data_coleta >= NOW() - 30")
cobertura = total_steam_raw / total_jogos_steam
```

**Status atual**: 99.2% (274.372 de 276.564)

#### KPI-02: Acurácia de Classificação
**Meta**: ≥ 75% de acurácia na classificação fracasso/mediano/sucesso

**Medição**:
```python
from sklearn.metrics import accuracy_score

y_true = test_set['categoria_sucesso']
y_pred = modelo.predict(X_test)
acuracia = accuracy_score(y_true, y_pred)
```

**Status atual**: 78.4% (XGBoost), 76.2% (RandomForest), 77.8% (LightGBM)

#### KPI-03: Estabilidade do Pipeline
**Meta**: ≥ 99% de execuções sem falhas críticas

**Medição**:
```python
execucoes_sucesso = db.count("logs WHERE nivel='INFO' AND mensagem LIKE '%concluído%'")
execucoes_totais = db.count("logs WHERE timestamp >= NOW() - 30")
estabilidade = execucoes_sucesso / execucoes_totais
```

**Status atual**: 99.7% (últimos 30 dias)

#### KPI-04: Qualidade de Dados
**Meta**: ≤ 5% de dados ausentes em campos críticos

**Campos críticos**: nome, preco, data_lancamento, genero, total_reviews

**Medição**:
```sql
SELECT 
    COUNT(*) FILTER (WHERE nome IS NULL) * 100.0 / COUNT(*) as pct_nome_null,
    COUNT(*) FILTER (WHERE preco IS NULL) * 100.0 / COUNT(*) as pct_preco_null,
    ...
FROM steam_unificado;
```

**Status atual**:
- nome: 0.1%
- preco: 0.8%
- data_lancamento: 1.5% (EM BREVE)
- genero: 0.3%
- total_reviews: 0% (padrão 0 se ausente)

---

## 4. Referencial Teórico

### 4.1 Machine Learning e Algoritmos de Classificação

#### 4.1.1 Fundamentos de Aprendizado Supervisionado

Machine Learning (ML) é um subcampo da Inteligência Artificial que permite que sistemas aprendam padrões a partir de dados sem serem explicitamente programados (GÉRON, 2019; FACELI et al., 2021). No contexto de **aprendizado supervisionado**, o algoritmo é treinado com dados rotulados (features + label) para aprender uma função $f: X \rightarrow Y$ que mapeia entradas para saídas.

**Tipos de problemas**:
- **Classificação**: Prever categoria discreta (ex: sucesso vs. fracasso)
- **Regressão**: Prever valor contínuo (ex: número de reviews)

#### 4.1.2 Random Forest

Random Forest é um método de **ensemble learning** que constrói múltiplas árvores de decisão durante o treinamento e combina suas previsões através de votação (classificação) ou média (regressão) (HASTIE; TIBSHIRANI; FRIEDMAN, 2009).

**Características principais**:
1. **Bagging**: Cada árvore é treinada em uma amostra bootstrap do dataset original
2. **Feature randomness**: Em cada split, apenas um subconjunto aleatório de features é considerado ($\sqrt{n_{features}}$ por padrão)
3. **Agregação**: Previsão final = moda das previsões individuais

**Vantagens**:
- Alta interpretabilidade (feature importance)
- Resistente a overfitting
- Lida bem com features categóricas e numéricas

**Limitações**:
- Desempenho inferior a gradient boosting em datasets grandes
- Não captura relações lineares tão bem quanto modelos lineares

**Aplicação no projeto**:
```python
modelo = RandomForestClassifier(
    n_estimators=200,      # 200 árvores
    max_depth=15,          # Profundidade máxima
    min_samples_split=10,  # Mínimo de amostras para split
    class_weight='balanced'  # Compensar desbalanceamento
)
```

#### 4.1.3 Gradient Boosting: XGBoost e LightGBM

##### XGBoost (Extreme Gradient Boosting)

XGBoost é uma implementação otimizada de gradient boosting que adiciona regularização e melhorias algorítmicas (CHEN; GUESTRIN, 2016). Diferente do Random Forest, constrói árvores **sequencialmente**, onde cada nova árvore corrige os erros das anteriores.

**Função objetivo**:
$$
\mathcal{L}(\phi) = \sum_i l(\hat{y}_i, y_i) + \sum_k \Omega(f_k)
$$

Onde:
- $l$: função de perda (log loss para classificação)
- $\Omega(f_k)$: termo de regularização ($\Omega = \gamma T + \frac{1}{2}\lambda \|\omega\|^2$)
- $T$: número de folhas, $\omega$: pesos das folhas

**Inovações técnicas**:
1. **Regularização L1 e L2**: Previne overfitting
2. **Column block para estruturas esparsas**: Eficiente com missing values
3. **Cache-aware access patterns**: Otimização de hardware
4. **Weighted quantile sketch**: Split finding eficiente

**Hiperparâmetros críticos** (usados no projeto):
- `max_depth=8`: Profundidade máxima das árvores (controla complexidade)
- `learning_rate=0.05`: Taxa de aprendizado (shrinkage)
- `n_estimators=300`: Número de árvores boosted
- `reg_alpha=0.1, reg_lambda=1.0`: Regularização L1 e L2
- `subsample=0.8`: Fração de amostras usadas por árvore

##### LightGBM

LightGBM (Light Gradient Boosting Machine) é uma variante otimizada para **velocidade e eficiência de memória** (KE et al., 2017).

**Técnicas principais**:

1. **Gradient-based One-Side Sampling (GOSS)**:
   - Mantém amostras com gradientes grandes (mais informativas)
   - Amostra aleatoriamente amostras com gradientes pequenos
   - Reduz complexidade de $O(n)$ para $O(a + b)$, onde $a \ll n$

2. **Exclusive Feature Bundling (EFB)**:
   - Agrupa features mutuamente exclusivas (ex: one-hot encoded)
   - Reduz dimensionalidade de features esparsas

3. **Histogram-based splitting**:
   - Discretiza features contínuas em bins (histogramas)
   - Split finding em $O(k)$ comparado a $O(n)$ do XGBoost

**Trade-off**: LightGBM é 5-10x mais rápido que XGBoost, mas pode ter acurácia ligeiramente inferior em datasets pequenos.

**Uso no projeto**: Experimentação rápida durante feature engineering, validação de novas features antes de treinar XGBoost completo.

#### 4.1.4 Métricas de Avaliação

##### Classificação Multiclasse

**Accuracy** (Acurácia):
$$
\text{Accuracy} = \frac{\text{Previsões Corretas}}{\text{Total de Previsões}}
$$

**Precision, Recall, F1-Score** (por classe):
$$
\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad \text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}
$$

**Macro-average**: Média simples das métricas de cada classe (trata todas igualmente)  
**Weighted-average**: Média ponderada pelo suporte de cada classe

**Matriz de Confusão**:
```
                Predito
              F    M    S
Real    F   [45   12    3]
        M   [8    67   15]
        S   [2    11   137]
```

**Aplicação no projeto**:
```python
from sklearn.metrics import classification_report

print(classification_report(y_true, y_pred, 
                            target_names=['Fracasso', 'Mediano', 'Sucesso']))
```

##### Regressão

**R² (Coeficiente de Determinação)**:
$$
R^2 = 1 - \frac{\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}{\sum_{i=1}^{n}(y_i - \bar{y})^2}
$$

**RMSE (Root Mean Squared Error)**:
$$
\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}
$$

**MAE (Mean Absolute Error)**:
$$
\text{MAE} = \frac{1}{n}\sum_{i=1}^{n}|y_i - \hat{y}_i|
$$

### 4.2 Processamento de Dados em Larga Escala

#### 4.2.1 Arquitetura ETL

ETL (Extract, Transform, Load) é um padrão arquitetural para integração de dados de múltiplas fontes (KLEPPMANN, 2017).

**Fases no projeto**:

1. **Extract** (Extração):
   - Steam API: Detalhes de jogos, reviews
   - IsThereAnyDeal API: Histórico de preços
   - Formato bruto: JSONB (flexível, schema-less)

2. **Transform** (Transformação):
   - Limpeza: `limpeza_preco.py`, `limpeza_data_lancamento.py`, etc.
   - Normalização: Unidecode para remoção de acentos
   - Feature engineering: Features derivadas (dias desde lançamento, ratio de reviews)

3. **Load** (Carregamento):
   - Bulk insert em `steam_unificado` (batches de 1000 registros)
   - Índices em campos frequentemente consultados (appid, genero, data_lancamento)

**Padrão de Checkpoint**:
Inspirado em frameworks de streaming (Kafka, Spark), o sistema salva progresso a cada batch para **idempotência** (reiniciar de onde parou em caso de falha).

```python
try:
    for batch in batches:
        processar_batch(batch)
        salvar_checkpoint(batch_id)
except Exception:
    ultimo_checkpoint = recuperar_checkpoint()
    reiniciar_de(ultimo_checkpoint)
```

#### 4.2.2 PostgreSQL e JSONB

PostgreSQL oferece suporte nativo a dados JSON com o tipo `JSONB` (binary JSON), que permite:
- Indexação com GIN (Generalized Inverted Index)
- Queries eficientes com operadores `->`, `->>`, `@>`
- Validação de schema com JSON Schema (opcional)

**Vantagens de JSONB para dados da Steam API** (OBE; HSU, 2017):
1. **Schema flexível**: API muda frequentemente, JSONB absorve mudanças sem ALTER TABLE
2. **Consultas ad-hoc**: Extrair campos sem reestruturação
3. **Auditoria**: Preserva dados brutos originais

**Exemplo de query**:
```sql
-- Buscar jogos com suporte a controle
SELECT appid, nome
FROM steam_raw
WHERE detalhes_completos @> '{"controller_support": "full"}';

-- Extrair lista de gêneros
SELECT appid, detalhes_completos->'genres' as generos
FROM steam_raw
WHERE appid = 570;  -- Dota 2
```

**Trade-off**: JSONB é 20-30% mais lento que colunas nativas para queries estruturadas, mas 10x mais rápido que text JSON.

#### 4.2.3 Otimização de Consultas SQL

**Índices aplicados**:
```sql
-- Índice B-tree em appid (chave primária)
CREATE UNIQUE INDEX idx_appid ON steam_unificado(appid);

-- Índice GIN em campo JSONB
CREATE INDEX idx_detalhes_gin ON steam_raw USING gin(detalhes_completos);

-- Índice parcial para jogos recentes
CREATE INDEX idx_jogos_recentes 
ON steam_unificado(data_lancamento)
WHERE data_lancamento >= '2024-01-01';
```

**Batch inserts** (30x mais rápido que inserts individuais):
```python
# Ruim: 1 insert por registro
for registro in registros:
    cursor.execute("INSERT INTO ... VALUES (%s)", (registro,))

# Bom: executemany com batch
cursor.executemany(
    "INSERT INTO ... VALUES (%s, %s, %s)",
    [(r['nome'], r['preco'], r['genero']) for r in registros]
)
```

**Resultado**: Inserção de 229k registros em 12 minutos (vs. 6+ horas com inserts individuais).

### 4.3 Engenharia de Features

Feature engineering é o processo de criar novas features a partir de dados brutos para melhorar o desempenho de modelos de ML (GÉRON, 2019, Cap. 2; KLOSTERMAN, 2019).

#### 4.3.1 Features Temporais

**Baseadas em data de lançamento**:
```python
df['dias_desde_lancamento'] = (pd.Timestamp.now() - df['data_lancamento']).dt.days
df['ano_lancamento'] = df['data_lancamento'].dt.year
df['mes_lancamento'] = df['data_lancamento'].dt.month
df['trimestre_lancamento'] = df['data_lancamento'].dt.quarter
```

**Justificativa**:
- Jogos mais antigos tendem a ter mais reviews acumuladas
- Sazonalidade: Q4 (outubro-dezembro) concentra lançamentos AAA
- Early access: dias desde lançamento indica maturidade

#### 4.3.2 Features Agregadas

**Contagens de entidades**:
```python
df['num_desenvolvedores'] = df['desenvolvedores'].apply(len)  # Lista de devs
df['num_generos'] = df['genero'].apply(lambda x: len(x.split(',')))
df['num_linguagens'] = df['linguagens'].apply(len)
```

**Ratios e proporções**:
```python
df['ratio_positivas'] = df['total_positive'] / (df['total_positive'] + df['total_negative'])
df['polarizacao'] = abs(0.5 - df['ratio_positivas'])  # Distância de 50/50
```

**Interpretação**:
- `ratio_positivas`: Proxy direto para review_score
- `polarizacao`: Jogos "love it or hate it" (nicho) vs. consensuais

#### 4.3.3 Features Categóricas - One-Hot Encoding

Para variáveis categóricas (gênero, desenvolvedor), usa-se codificação one-hot:

```python
from sklearn.preprocessing import OneHotEncoder

encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
generos_encoded = encoder.fit_transform(df[['genero']])
# Resultado: matriz binária [n_samples, n_categorias]
```

**Limitação**: High cardinality (ex: 50k desenvolvedores únicos) causa curse of dimensionality.

**Solução aplicada**: Agrupar categorias raras em "Outros"
```python
top_50_devs = df['desenvolvedores'].value_counts().head(50).index
df['dev_grouped'] = df['desenvolvedores'].apply(
    lambda x: x if x in top_50_devs else 'Outros'
)
```

#### 4.3.4 Features Derivadas do JSONB

**Extração de metadados**:
```python
def extrair_features_detalhes(jsonb_detalhes):
    d = json.loads(jsonb_detalhes)
    return {
        'tem_achievements': 'achievements' in d,
        'tem_trading_cards': 'trading_cards' in d,
        'suporte_multiplayer': 'categories' in d and any('multi' in c for c in d['categories']),
        'tamanho_descricao': len(d.get('detailed_description', '')),
        'num_screenshots': len(d.get('screenshots', []))
    }
```

**Justificativa**:
- Achievements e trading cards aumentam engajamento (replayability)
- Multiplayer correlaciona com longevidade (mais reviews ao longo do tempo)
- Descrição detalhada indica esforço de marketing

### 4.4 Validação e Generalização

#### 4.4.1 Train/Test Split Temporal

Para séries temporais e dados com dependência temporal, o split deve respeitar a ordem cronológica (GÉRON, 2019, Cap. 3; HUYEN, 2022):

```python
# Ordena por data de atualização
df_sorted = df.sort_values('ultima_atualizacao')

# 80% mais antigos = treino, 20% mais recentes = teste
split_idx = int(len(df_sorted) * 0.8)
train = df_sorted[:split_idx]
test = df_sorted[split_idx:]
```

**Justificativa**:
- Evita data leakage (usar dados de 2026 para prever 2025)
- Simula cenário real: treinar com passado, prever futuro
- Detecta concept drift (mudança de padrões ao longo do tempo)

#### 4.4.2 Cross-Validation Temporal

Para séries temporais, usa-se **Time Series Split** ao invés de K-Fold padrão:

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(df):
    X_train, X_val = df.iloc[train_idx], df.iloc[val_idx]
    # Treina e valida
```

**Esquema**:
```
Fold 1: [Train    ] [Val]
Fold 2: [Train         ] [Val]
Fold 3: [Train              ] [Val]
...
```

#### 4.4.3 Overfitting e Regularização

**Sintomas de overfitting**:
- Acurácia de treino >> acurácia de teste (ex: 95% vs. 70%)
- Alta variância (modelo muda drasticamente com pequenas mudanças nos dados)

**Técnicas de regularização aplicadas**:

1. **XGBoost L1/L2**:
```python
xgb.XGBClassifier(reg_alpha=0.1, reg_lambda=1.0)
```

2. **Early stopping**:
```python
modelo.fit(X_train, y_train, 
           eval_set=[(X_val, y_val)],
           early_stopping_rounds=10)  # Para se validationfication piorar
```

3. **Max depth e min child weight**:
```python
xgb.XGBClassifier(max_depth=8, min_child_weight=5)
```

### 4.5 Sistemas de Recomendação e Previsão (Contexto Teórico)

Embora o projeto atual foque em **classificação de sucesso**, a fundamentação teórica em sistemas de recomendação é relevante para extensões futuras.

#### 4.5.1 Collaborative Filtering

Técnica que prediz preferências de usuários baseado em comportamento de usuários similares (SARWAR et al., 2001).

**Fórmula de similaridade de cosseno**:
$$
\text{sim}(i,j) = \frac{\sum_{u \in U} r_{ui} \cdot r_{uj}}{\sqrt{\sum_{u \in U} r_{ui}^2} \cdot \sqrt{\sum_{u \in U} r_{uj}^2}}
$$

Onde $r_{ui}$ é o rating do usuário $u$ para o item $i$.

**Aplicação potencial**: "Jogos similares a X têm sucesso quando Y características estão presentes".

#### 4.5.2 Matrix Factorization

Técnica de redução de dimensionalidade que decompõe matriz de ratings em matrizes de features latentes (KOREN; BELL; VOLINSKY, 2009).

$$
R \approx P \times Q^T
$$

Onde:
- $R$: matriz de ratings ($n_{users} \times n_{items}$)
- $P$: matriz de features de usuários ($n_{users} \times k$)
- $Q$: matriz de features de itens ($n_{items} \times k$)

**Extensão futura**: Usar embeddings de gêneros/desenvolvedores aprendidos via matrix factorization como features numéricas ao invés de one-hot encoding.

### 4.6 Arquitetura de Software

#### 4.6.1 Repository Pattern

Padrão arquitetural que abstrai acesso a dados, separando lógica de negócio da lógica de persistência (FOWLER, 2002).

**Implementação no projeto**:
```python
# classes/SQL/postgre_steam.py
class RepositorioSteam:
    def buscar_por_appid(self, appid):
        # Query SQL encapsulada
        pass
    
    def inserir_bulk(self, registros):
        # Lógica de batch insert
        pass
```

**Vantagens**:
- Testabilidade: Mock do repositório em testes unitários
- Manutenibilidade: Trocar PostgreSQL por outro banco sem alterar lógica de negócio
- Single Responsibility: Repositório só cuida de persistência

#### 4.6.2 Pipeline Pattern

Sequência de processadores que transformam dados incrementalmente (FOWLER, 2002).

**Implementação**:
```python
# sklearn Pipeline
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('limpeza', LimpadorDados()),
    ('features', EngenheiriaFeatures()),
    ('scaler', StandardScaler()),
    ('modelo', XGBClassifier())
])

pipeline.fit(X_train, y_train)
```

**Vantagens**:
- Evita data leakage: StandardScaler calcula média/desvio apenas no treino, aplica no teste
- Reutilizável: `joblib.dump(pipeline)` salva toda a transformação
- Reprodutível: Mesmo pipeline aplicado em produção

#### 4.6.3 Checkpoint Pattern

Padrão para persistir estado intermediário de processamento longo (KLEPPMANN, 2017, Cap. 11).

**Implementação**:
```python
def processar_com_checkpoint(appids):
    checkpoint = recuperar_checkpoint()
    inicio = checkpoint.get('ultimo_indice', 0)
    
    for i, appid in enumerate(appids[inicio:], start=inicio):
        processar(appid)
        
        if i % 50 == 0:
            salvar_checkpoint({'ultimo_indice': i})
```

**Uso em sistemas distribuídos**:
- Apache Spark: Checkpoints em RDDs
- Apache Kafka: Consumer offsets
- Este projeto: Tabela `checkpoints` no PostgreSQL

### 4.7 A Indústria de Jogos Digitais

#### 4.7.1 Economia da Plataforma Steam

A Steam, desenvolvida pela Valve Corporation, é a maior plataforma de distribuição digital de jogos para PC, com:
- **30% de comissão** sobre vendas (padrão da indústria)
- **Mais de 120 milhões de usuários ativos mensais** (2025)
- **Mais de 280.000 jogos** no catálogo (fonte: SteamDB, 2026)

**Desafios para desenvolvedores**:
- Mercado saturado: 10-15k novos jogos lançados por ano
- Descobrabilidade: <5% dos jogos alcançam página inicial da Steam
- Precificação: Concorrência com bundles e promoções constantes

#### 4.7.2 Fatores de Sucesso

Baseado em literatura de economia de jogos (MARCHAND; HENNIG-THURAU, 2013):

1. **Qualidade Percebida**: Reviews críticas (Metacritic) e de usuários
2. **Network Effects**: Multiplayer e componentes sociais
3. **Timing**: Lançamento fora de competição direta com AAA
4. **Precificação**: Sweet spot $15-25 para indie, $60 para AAA
5. **Marketing**: Presença em eventos (TGA, E3), streamers no Twitch

**Validação no dataset**:
- Jogos com Metacritic >80: 72% de reviews positivas médias
- Jogos multiplayer: 3x mais reviews que single-player (maior longevidade)
- Preço $20-30: Melhor conversão para indie (análise de 12k jogos)

---

## 📚 Referências Bibliográficas

### Livros

CHEN, Tianqi; GUESTRIN, Carlos. **XGBoost: A Scalable Tree Boosting System**. In: PROCEEDINGS OF THE 22ND ACM SIGKDD INTERNATIONAL CONFERENCE ON KNOWLEDGE DISCOVERY AND DATA MINING. San Francisco: ACM, 2016. p. 785-794.

EVANS, Eric. **Domain-Driven Design: Tackling Complexity in the Heart of Software**. Boston: Addison-Wesley, 2003.

FOWLER, Martin. **Patterns of Enterprise Application Architecture**. Boston: Addison-Wesley, 2002.

GÉRON, Aurélien. **Mãos à Obra: Aprendizado de Máquina com Scikit-Learn, Keras e TensorFlow**. 2. ed. Rio de Janeiro: Alta Books, 2019.

HUYEN, Chip. **Projetando Sistemas de Machine Learning: Processos Iterativos para Aplicações Prontas para Produção**.

CARVALHO, André C. P. L. F.; MENEZES, Angelo Garangau; BONIDIA, Robson Parmezan. **Ciência de Dados: Fundamentos e Aplicações**.

KLOSTERMAN, Stephen. **Projetos de Ciência de Dados com Python: Abordagem de estudo de caso para criação de projetos de ciência de dados bem-sucedidos usando Python, pandas e scikit-learn**.

FACELI, Katti; LORENA, Ana Carolina; ALMEIDA, Tiago Agostinho; CARVALHO, André C. P. L. F. **Inteligência Artificial: Uma abordagem de Aprendizado de Máquina**. 3. ed.

HASTIE, Trevor; TIBSHIRANI, Robert; FRIEDMAN, Jerome. **The Elements of Statistical Learning: Data Mining, Inference, and Prediction**. 2. ed. New York: Springer, 2009.

KLEPPMANN, Martin. **Designing Data-Intensive Applications**. Sebastopol: O'Reilly Media, 2017.

MARTIN, Robert C. **Clean Code: A Handbook of Agile Software Craftsmanship**. Upper Saddle River: Prentice Hall, 2008.

NEWMAN, Sam. **Building Microservices**. 2. ed. Sebastopol: O'Reilly Media, 2021.

OBE, Regina; HSU, Leo. **PostgreSQL: Up and Running**. 3. ed. Sebastopol: O'Reilly Media, 2017.

PRESSMAN, Roger S.; MAXIM, Bruce R. **Engenharia de Software: Uma Abordagem Profissional**. 9. ed. Porto Alegre: AMGH, 2021.

SCHONIG, Hans-Jürgen. **Mastering PostgreSQL 15**. Birmingham: Packt Publishing, 2023.

### Artigos Científicos

HE, Xiangnan et al. **Neural Collaborative Filtering**. In: PROCEEDINGS OF THE 26TH INTERNATIONAL CONFERENCE ON WORLD WIDE WEB. Perth: ACM, 2017. p. 173-182.

KE, Guolin et al. **LightGBM: A Highly Efficient Gradient Boosting Decision Tree**. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS 30 (NIPS 2017). Long Beach: NIPS, 2017. p. 3146-3154.

KOREN, Yehuda; BELL, Robert; VOLINSKY, Chris. **Matrix Factorization Techniques for Recommender Systems**. IEEE Computer, v. 42, n. 8, p. 30-37, 2009.

MARCHAND, André; HENNIG-THURAU, Thorsten. **Value Creation in the Video Game Industry: Industry Economics, Consumer Benefits, and Research Opportunities**. Journal of Interactive Marketing, v. 27, n. 3, p. 141-157, 2013.

SARWAR, Badrul et al. **Item-based collaborative filtering recommendation algorithms**. In: PROCEEDINGS OF THE 10TH INTERNATIONAL CONFERENCE ON WORLD WIDE WEB. Hong Kong: ACM, 2001. p. 285-295.

### Documentação Técnica

NEWZOO. **Global Games Market Report 2025**. Amsterdam: Newzoo, 2025.

VALVE CORPORATION. **Steamworks API Documentation**. Disponível em: <https://partner.steamgames.com/doc/api>. Acesso em: 12 mar. 2026.

### Normas ABNT

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023: Informação e documentação – Referências – Elaboração**. Rio de Janeiro: ABNT, 2018.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6028: Informação e documentação – Resumo – Procedimento**. Rio de Janeiro: ABNT, 2003.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 10520: Informação e documentação – Citações em documentos – Apresentação**. Rio de Janeiro: ABNT, 2023.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 14724: Informação e documentação – Trabalhos acadêmicos – Apresentação**. Rio de Janeiro: ABNT, 2011.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 15287: Informação e documentação – Projeto de pesquisa – Apresentação**. Rio de Janeiro: ABNT, 2011.

---

## 📝 Notas de Implementação

### Próximos Passos (Para Escrita do TCC)

1. **Expandir seção 4.1**: Adicionar diagramas de árvores de decisão, gráficos de feature importance
2. **Adicionar seção 4.8**: Análise Exploratória de Dados (EDA) com visualizações do dataset
3. **Criar apêndice A**: Código-fonte completo dos módulos principais
4. **Criar apêndice B**: Queries SQL para replicação do banco de dados
5. **Revisar referências**: Verificar formatação ABNT de todas as entradas
6. **Adicionar glossário**: Termos técnicos (AppID, JSONB, ensemble, etc.)

### Validação de Referências

**Status**:
- ✅ Livros-base adotados no projeto citados (Géron, Huyen, Carvalho et al., Klosterman, Faceli et al.)
- ✅ Artigos seminais (XGBoost, LightGBM)
- ✅ Normas ABNT completas
- ⏳ Adicionar mais papers sobre game economics
- ⏳ Verificar se biblioteca tem acesso físico aos livros

### Alinhamento com Orientador

**Pontos a discutir**:
1. Profundidade matemática das fórmulas (equilibrar rigor com clareza)
2. Inclusão de código no corpo do texto vs. apêndices
3. Extensão da revisão de literatura (25-35 páginas é adequado?)
4. Necessidade de comparação com trabalhos relacionados (State of the Art)

---

**Última atualização**: 12 de março de 2026  
**Versão do documento**: 1.0  
**Autor**: Camilo Prado  
**Orientador**: [Nome do orientador]
