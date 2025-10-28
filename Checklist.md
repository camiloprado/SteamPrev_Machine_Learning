# Checklist de Machine Learning - RETIRADO DE "MÃOS À OBRA: APRENDIZADO DE MÁQUINA COM SCIKIT-LEARN, KERAS E TENSORFLOW" DE AURÉLIEN GÉRON - PG 579-582

1. ABORDAR O PROBLEMA E ANALISAR O PANORAMA EM GERAL
2. OBTER OS DADOS
3. EXPLORAR OS DADOS PARA OBTER INFORMAÇÕES ÚTEIS
4. PREPARAR OS DADOS PARA EXPOR MELHOR OS PADRÕES DE DADOS SUBJACENTES AOS ALGORITMOS DE MACHINE LEARNING
5. EXPLORAR MUITOS MODELOS DIFERENTES E SELECIONAR OS MELHORES
6. APERFEIÇOAR SEUS MODELOS E OS COMBINAR EM UMA SOLUÇÃO IDEAL
7. APRESENTAR SUA SOLUÇÃO
8. IMPLEMENTAR, MONITORAR E FAZER A MANUTENÇÃO DE SEU SISTEMA

## ABORDAR O PROBLEMA E ANALISAR O PANORAMA EM GERAL
1. Definir o objetivo em termos de negócios.
2. Como sua solução será usada?
3. Quais são as soluções/alternativas atuais (caso existam)?
4. Como você deve abordar este problema (aprendizado supervisionado/não supervionado, online/offline, etc.)?
5. Como o desempenho deve ser medido?
6. A medida de desempenho está alinhada com o objetivo do negócio?
7. Qual seria o desempenho mínimo necessário para alcançar o objetivo do negócio?
8. O que são problemas comparáveis? Você pode reutilizar experiências ou ferramentas?
9. Tem expertise humana disponível?
10. Como você resolveria o problema manualmente?
11. Enumere as suposições que você (ou outras pessoas) fizeram até agora.
12. Verifique essas suposições, se possivel

## OBTER OS DADOS
* Nota: Automatize o máximo possível para que possa obter dados atualizados com facilidade.
1. Liste os dados de que você precisa e de quanto precisa.
2. Encontre e documente onde você pode obter esses dados.
3. Verifique quanto espaço esses dados ocuparão.
4. Verifique as obrigações legais e obtenha autorização, se necessário.
5. Obtenha permissão de acesso.
6. Crie um workspace (com espaço de armazenamento suficiente).
7. Obtenha os dados.
8. Converta os dados em um formatdo que você possa manipular com facilidade (sem alterar os prórpios dados).
9. Assegure que as informações confidenciasis sejam excluídas ou protegidas (por exemplo, deixando-as anônimas).
10. Verifique o tamanho e o tipo de dados (série temporal, amostrados, geográficos, etc.).
11. Amostre um conjunto de teste, deixe-o de lado e nem coloque a mãe nele (sem data snooping, hein?).

## EXPLORE OS DADOS
* Nota: Procure um especialista de campo para estas etapas.

1. Crie uma cópia dos dados para exploração (amostragem até um tamanho gerenciável, se necessário).
2. Crie um Jupyter Notebook para manter um registro de sua exploração de dados.
3. Estude cada atributo e suas propriedades:
    * Nome.
    * Tipo (categórico, int/float, bounded/unbounded, texto, estruturado, etc.).
    * % de valores ausentes.
    * Ruído e tipo de ruído (estocástico, outliers, erros de arredondamento, etc.).
    * Utilidade para a tarefa.
    * Tipo de distribuição (gaussiana, uniforme, logarítmica, etc.).
4. Para tarefas de aprendizado supervisionado, identifique o(s) atributo(s)-alvo.
5. Visualize os dados. 
6. Estude as correlações entre os atribustos.
7. Estude como você resolveria o problema manualmente.
8. Identifique as transformações promissoras que você pode querer aplicar.
9. Identifique dados extras que seriam úteis.
10. Documente o que você aprendeu.

## PREPARE OS DADOS
* Notas: 
    - Trabalhe em cópias dos dados (mantenha o conjunto de dados original intacto).
    - Escreva funções para todas as transformações de dados que você aplicar, por cinco motivos:
    - Desse modo, você consegue preparar facilmente os dados da próxima vez que obtiver um novo conjunto de dados.
    - Assim, você pode aplicar essas transformações em projetos futuros para: 
    - Limpar e preparar o conjuto de teste
    - Limpar e preparar novas instâncias de dados assim que sua solução estiver em produção
    - Facilitar o tratamento de suas escolhas de preparação como hiperparâmetros.

1. Limpeza de dados:
    * Corrige ou remove outliers (opcional).
    * Preenche os valores ausentes (por exemplo, com zero, média, mediana...) ou elimina suas linhas (ou colunas).
2. Seleção de características (opcional):
    * Dropa os atributos que não fornecem informações úteis para a tarefa.
3. Feature engineering, quando apropriado:
    * Discretiza características contínuas.
    * Decompõe as características (por exemplo, categóricas, data/hora, etc.).
    * Adiciona transformações promissoras de características (ex.: log(x), sqrt(x), x², etc.).
4. Escalonamento de características
    * Padroniza ou normaliza as características.
    
## PRÉ-SELEÇÃO DE MODELOS PROMISSORES
* Notas:
    - Se os dados forem enormes, você pode amostrar conjuntos de treinamento menores para que possa treina muitos modelos diferentes em um tempo razoável (esteja ciente de que isso penaliza modelos complexos, como grandes redes neurais ou florestas aleatórias).
    - Mais uma vez, tente automatizar essas etapas o máximo possível.

1. Treine muitos modelos rápidos e simples de diferentes categorias (por exemplo, linear, naive Bayes, SVM, floresta aleatórias, rede neural, etc.) usando parâmetros-padrão.
2. Meça e compare seu desempenho:
    * Para cada modelo, use a validação cruzada N-Fold e calcule a média e o desvio-padrão da medida de desempenho nas N-Folds.
3. Analise as variáveis mais significativas para cada algoristmo.
4. Analise os tipos de erros que os modelos cometem.
    * Quais dados um humano teria usado para evitar esses erros?
5. Execute uma rodada rápida de seleção de características e feature engineering.
6. Rode mais uma ou duas iterações rápidas das cinco etapas anteriores
7. Faça uma pré-seleção de três a cinco modelos mais promissores, preferindo modelos que cometam diferentes tipos de erros.

## APERFEIÇOE SEU SISTEMA
* Notas: 
    - Você desejará usar o máximo de dados possíveis para essa etapa, sobretudo à medida que avança para aperfeiçoamento.
    - Como sempre, automatize o que for possível.
1. Ajuste os hiperparâmetros usando validação cruzada:
    * Trate suas opções de transformação de dados como hiperparâmetros, ainda mais quando você não estiver certo sobre elas (por exemplo, se não tiver certeza se deve substituir os valores ausentes por zeros ou pelo valor mediano, ou apenas dropar as linhas).
    * A menos que haja poucos valores de hiperparâmetros para explorar, prefira o random search em vez de grid search. Se o treinamento for muito longo, você pode preferir uma abordagem de otimização bayesiana (por exemplo, usando processos gaussianos anteriores conforme descrito por Jasper Snoeck).
2. Teste os métodos ensemble. Combinar seus melhores modelos geralmente resultará em um melhor desempenho do que executá-los individualmente.
3. Uma vez que você esteja confiante sobre seu modelo final, meça seu desempenho no conjunto de testes para estimar o erro de generalização.

* Aviso: Não ajuste seu modelo depois de medir o erro de generalização: você simplesmente começaria a ajudar o conjunto de teste.

## APRESENTE SUA SOLUÇÃO
1. Documente o que você fez.
2. Crie uma boa apresentação.
    * Faça questão de primeiro ressaltar o panorama em geral.
3. Explique por que sua solução alcança o objetivo de negócio.
4. Não se esqueça de aprensetar pontos interessantes que você identificou ao longo do caminho.
    * Descreva o que funcionou e o que não funcionou.
    * Enumere suas suposições e as limitações do seu sistema.
5. Certifique-se de que suas principais descobertas sejam comunicadas por meio de belas visualizações ou declarações fáceis de lembrar (por exemplo, "a renda média é o preditor número um dos preços de imóveis").

## IMPLEMENTE!
1. Prepare sua solução para produção (conecte-a às entradas de dados de produção, escreva testes unitários, etc.).
2. Escreva o código de monitoramento para verificar o desempenho ao vivo do seu sistema em intervalos regulares e acione alertas quando ele cair.
    * Cuidado com a degradação lenta: os modelos tendem a "apodrecer" conforme os dados evoluem.
    * A medição do desempenho pode exigir um pipeline humano (por exemplo, por meio de um serviço de crowdsourcing).
    * Monitore também a qualidade de suas entradas (por exemplo, um sensor com defeito que envia valores aleatórios ou a saída de outra equipe se tornando obsoleto). Isso é muito importante para sistemas de aprendizado online.
3. Treine novamente seus modelos regularmente com base em dados atualizados (automatize o máximo possível).

# Exemplo de Respostas para o Projeto "Previsor Steam"

## ABORDAR O PROBLEMA E ANALISAR O PANORAMA EM GERAL
1. **Definir o objetivo em termos de negócios:** Criar um modelo que preveja o potencial de sucesso de um jogo na Steam (ex: volume de vendas, popularidade ou receita) para auxiliar desenvolvedores e publishers na tomada de decisões estratégicas.
2. **Como sua solução será usada?** A solução pode ser uma API ou um dashboard onde, ao inserir dados de um jogo (gênero, preço, etc.), o sistema retorna uma previsão de desempenho.
3. **Quais são as soluções/alternativas atuais?** Análise de mercado manual, consultorias especializadas e ferramentas de análise de mercado como SteamSpy.
4. **Como você deve abordar este problema?** Aprendizado supervisionado. Pode ser um problema de **regressão** (para prever um valor numérico, como receita ou número de reviews) ou **classificação** (para prever uma categoria de sucesso, como "fracasso", "médio", "sucesso"). O treinamento será **offline**, com dados coletados periodicamente.
5. **Como o desempenho deve ser medido?**
    * **Regressão:** Erro Quadrático Médio (RMSE) ou Erro Absoluto Médio (MAE).
    * **Classificação:** Acurácia, Precisão, Recall e F1-Score.
6. **A medida de desempenho está alinhada com o objetivo do negócio?** Sim. Medir o erro da previsão (RMSE/MAE) ou a capacidade de classificar corretamente o sucesso (F1-Score) está diretamente ligado à confiabilidade da ferramenta para a tomada de decisão.
7. **Qual seria o desempenho mínimo necessário?** Para regressão, um erro percentual médio abaixo de 25% seria um bom começo. Para classificação, uma acurácia acima de 70-75% seria um resultado inicial viável.
8. **O que são problemas comparáveis?** Previsão de bilheteira de filmes, previsão de preços de imóveis. Podemos reutilizar técnicas de feature engineering e modelos de regressão (Linear, Random Forest) e classificação (Logistic Regression, SVM) comuns nesses domínios.
9. **Tem expertise humana disponível?** Sim, a experiência de jogadores, desenvolvedores e analistas de mercado é valiosa para entender quais features (gênero, arte, marketing) são mais importantes.
10. **Como você resolveria o problema manualmente?** Um analista olharia para o gênero, histórico do desenvolvedor/publisher, preço, data de lançamento, marketing inicial e jogos similares para fazer uma estimativa de sucesso.
11. **Enumere as suposições:**
    * O sucesso passado de um desenvolvedor/publisher influencia o sucesso futuro.
    * Gêneros e categorias têm popularidade cíclica.
    * O preço inicial é um fator crucial para as vendas.
    * Reviews iniciais são um forte indicador de vendas a longo prazo.
12. **Verifique essas suposições:** A análise exploratória dos dados (correlações entre features e o alvo) pode validar ou invalidar essas suposições.

## OBTER OS DADOS
1. **Liste os dados de que você precisa:** Detalhes dos jogos (gênero, categorias, desenvolvedor, data de lançamento), preços, histórico de preços, número de reviews, score de reviews. Precisamos de dados de milhares de jogos para ter um modelo robusto.
2. **Encontre e documente onde você pode obter esses dados:** Steam API (para detalhes e reviews) e IsThereAnyDeal API (para histórico de preços). O projeto já implementa essa coleta.
3. **Verifique quanto espaço esses dados ocuparão:** Inicialmente, alguns gigabytes. O banco de dados PostgreSQL crescerá com o tempo.
4. **Verifique as obrigações legais:** Os Termos de Serviço das APIs da Steam e ITAD permitem o uso para projetos não comerciais/acadêmicos, desde que os limites de requisição sejam respeitados.
5. **Obtenha permissão de acesso:** Obter chaves de API. O projeto já possui uma chave para o ITAD.
6. **Crie um workspace:** O projeto já está estruturado no diretório atual.
7. **Obtenha os dados:** O script `GetTask.py` em conjunto com `steam_api.py` já realiza a coleta de dados.
8. **Converta os dados em um formato que você possa manipular:** Os dados são coletados em JSON e armazenados em um banco de dados PostgreSQL, um formato estruturado e fácil de manipular com Python (usando `psycopg2` e `pandas`).
9. **Assegure que as informações confidenciais sejam excluídas:** Não estamos coletando dados de usuários, apenas dados públicos dos jogos.
10. **Verifique o tamanho e o tipo de dados:** Temos dados numéricos (preço, score), categóricos (gênero, desenvolvedor), textuais (descrição) e de série temporal (data de lançamento, histórico de preços).
11. **Amostre um conjunto de teste:** Antes de iniciar a exploração e o treinamento, devemos separar ~20% dos dados para um conjunto de teste final, que não será tocado até a avaliação do modelo final.

## EXPLORE OS DADOS
1. **Crie uma cópia dos dados para exploração:** Carregue os dados do PostgreSQL para um DataFrame do Pandas.
2. **Crie um Jupyter Notebook:** Ideal para documentar a exploração com visualizações e anotações.
3. **Estude cada atributo:**
    * **Nome:** `nome`, `appid`, `preco`, `desenvolvedores`, `genero`, etc.
    * **Tipo:** `preco` (numérico), `genero` (categórico), `data_lancamento` (data/hora).
    * **% de valores ausentes:** Verificar colunas como `metacritic_score`, que podem ter muitos valores nulos.
    * **Ruído:** O campo `supported_languages` contém tags HTML que precisam ser limpas. O projeto já faz parte dessa limpeza.
    * **Utilidade:** `appid` é um identificador. `genero`, `preco` e `metacritic_score` são provavelmente muito úteis.
    * **Distribuição:** Analisar a distribuição dos preços, scores, etc. (ex: preços podem ter uma distribuição log-normal).
4. **Identifique o(s) atributo(s)-alvo:** Poderia ser a quantidade de reviews positivas (numérico) ou uma categoria de sucesso baseada no número total de reviews (categórico).
5. **Visualize os dados:** Criar histogramas para preços, gráficos de barras para gêneros e scatter plots para correlações (ex: `metacritic_score` vs. `reviews`).
6. **Estude as correlações:** Usar `df.corr()` para ver a correlação entre as features numéricas e o alvo.
7. **Estude como você resolveria o problema manualmente:** Um analista provavelmente daria mais peso a gêneros populares, desenvolvedores conhecidos e jogos com bom `metacritic_score`.
8. **Identifique as transformações promissoras:**
    * **Logaritmo do preço:** Para normalizar a distribuição.
    * **One-Hot Encoding:** Para `genero` e `categorias`.
    * **Contagem/Frequência:** Para `desenvolvedores` (transformar o nome do desenvolvedor em um número que representa sua popularidade/frequência).
9. **Identifique dados extras que seriam úteis:** Dados de marketing (não disponíveis), número de jogadores simultâneos (disponível via API).
10. **Documente o que você aprendeu:** Anotar as principais correlações e insights no Jupyter Notebook.

## PREPARE OS DADOS
1. **Limpeza de dados:**
    * **Outliers:** Analisar jogos com preços ou número de reviews extremamente altos. Decidir se devem ser removidos ou se o valor deve ser ajustado.
    * **Valores ausentes:** Para `metacritic_score`, preencher com a média ou mediana, ou criar uma categoria "desconhecido". O projeto atualmente salva como string vazia, o que precisa ser tratado.
2. **Seleção de características:** Remover atributos que não agregam valor (ex: URL da imagem do cabeçalho).
3. **Feature engineering:**
    * **Discretizar:** Transformar `data_lancamento` em "ano de lançamento" e "mês de lançamento".
    * **Decompor:** Extrair o número de linguagens suportadas.
    * **Transformações:** Aplicar `log(preco + 1)`.
