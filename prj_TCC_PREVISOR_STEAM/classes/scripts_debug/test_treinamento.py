import numpy as np
from zlib import crc32
class Treinamento_Teste:
    """
    Classe criada para fazer o treinamento de uma parcela de dados.
    """

    def split_train_test(self, data, test_ratio):
        """
        Divide os dados em conjuntos de treinamento e teste.

        Parâmetros:
        - data: Conjunto de dados a ser dividido.
        - test_ratio: Proporção dos dados que será usada para teste.

        Retorna:
        - train_data: Conjunto de dados de treinamento.
        - test_data: Conjunto de dados de teste.
        """
        shuffled_indices = np.random.permutation(len(data))
        test_set_size = int(len(data) * test_ratio)
        test_indices = shuffled_indices[:test_set_size]
        train_indices = shuffled_indices[test_set_size:]
        return data.iloc[train_indices], data.iloc[test_indices]
    
    def test_set_check(self, identifier, test_ratio):
        """
        Verifica se um dado pertence ao conjunto de teste com base em seu identificador.

        Parâmetros:
        - identifier: Identificador único do dado.
        - test_ratio: Proporção dos dados que será usada para teste.

        Retorna:
        - bool: True se o dado pertence ao conjunto de teste, False caso contrário.
        """
        return (crc32(np.int64(identifier)) & 0xffffffff) < test_ratio * 2**32
    
    def split_train_test_by_id(self, data, test_ratio, id_column):
        """
        Divide os dados em conjuntos de treinamento e teste com base em um identificador.

        Parâmetros:
        - data: Conjunto de dados a ser dividido.
        - test_ratio: Proporção dos dados que será usada para teste.
        - id_column: Nome da coluna que contém o identificador único.

        Retorna:
        - train_data: Conjunto de dados de treinamento.
        - test_data: Conjunto de dados de teste.
        """
        ids = data[id_column]
        in_test_set = ids.apply(lambda id_: self.test_set_check(id_, test_ratio))
        return data.loc[~in_test_set], data.loc[in_test_set]
    
    def stratified_split(self, data, strat_column, test_ratio):
        """
        Realiza uma divisão estratificada dos dados com base em uma coluna específica.

        Parâmetros:
        - data: Conjunto de dados a ser dividido.
        - strat_column: Nome da coluna usada para estratificação.
        - test_ratio: Proporção dos dados que será usada para teste.

        Retorna:
        - train_data: Conjunto de dados de treinamento.
        - test_data: Conjunto de dados de teste.
        """
        from sklearn.model_selection import StratifiedShuffleSplit

        split = StratifiedShuffleSplit(n_splits=1, test_size=test_ratio, random_state=42)
        for train_index, test_index in split.split(data, data[strat_column]):
            strat_train_set = data.loc[train_index]
            strat_test_set = data.loc[test_index]
        return strat_train_set, strat_test_set
    
    def table_stratifiedxrandom(self, data, strat_column, test_ratio):
        """
        Compara a divisão estratificada com uma divisão aleatória dos dados.
        Tabela:
        | OVERALL | RANDOM | STRATIFIED | RAND. %ERROR | STRAT. %ERROR |

        Parâmetros:
        - data: Conjunto de dados a ser dividido.
        - strat_column: Nome da coluna usada para estratificação.
        - test_ratio: Proporção dos dados que será usada para teste.

        Retorna:
        - None: Imprime as proporções dos conjuntos de treinamento e teste.
        """
        import pandas as pd
        
        # Proporções gerais nos dados originais
        overall_proportions = data[strat_column].value_counts() / len(data)
        
        # Divisão aleatória
        train_set, test_set = self.split_train_test(data, test_ratio)
        random_proportions = test_set[strat_column].value_counts() / len(test_set)

        # Divisão estratificada
        strat_train_set, strat_test_set = self.stratified_split(data, strat_column, test_ratio)
        stratified_proportions = strat_test_set[strat_column].value_counts() / len(strat_test_set)
        
        # Cria tabela comparativa
        comparison_table = pd.DataFrame({
            'OVERALL': overall_proportions,
            'RANDOM': random_proportions,
            'STRATIFIED': stratified_proportions
        })
        
        # Calcula erros percentuais
        comparison_table['RAND. %ERROR'] = ((comparison_table['RANDOM'] - comparison_table['OVERALL']) / 
                                             comparison_table['OVERALL'] * 100)
        comparison_table['STRAT. %ERROR'] = ((comparison_table['STRATIFIED'] - comparison_table['OVERALL']) / 
                                              comparison_table['OVERALL'] * 100)
        
        # Preenche valores ausentes com 0
        comparison_table = comparison_table.fillna(0)
        
        # Formata e imprime a tabela
        print("\n" + "="*80)
        print("COMPARAÇÃO: DIVISÃO ESTRATIFICADA vs DIVISÃO ALEATÓRIA")
        print("="*80)
        print(comparison_table.to_string())
        print("="*80)
        
        return comparison_table
    
    def create_price_category(self, data, price_column='price'):
        """
        Cria categorias de preço para estratificação.
        
        Parâmetros:
        - data: DataFrame com os dados
        - price_column: Nome da coluna de preço
        
        Retorna:
        - data: DataFrame com nova coluna 'price_category'
        """
        import pandas as pd
        
        data = data.copy()
        data['price_category'] = pd.cut(
            data[price_column],
            bins=[-0.01, 0, 10, 30, 100, float('inf')],
            labels=['free', 'budget', 'mid', 'premium', 'luxury']
        )
        
        print("\nDistribuição de categorias de preço:")
        print(data['price_category'].value_counts().sort_index())
        
        return data
    
    def create_popularity_category(self, data, review_column='total_reviews'):
        """
        Cria categorias de popularidade baseada no número de reviews.
        
        Parâmetros:
        - data: DataFrame com os dados
        - review_column: Nome da coluna de total de reviews
        
        Retorna:
        - data: DataFrame com nova coluna 'popularity_category'
        """
        import pandas as pd
        
        data = data.copy()
        data['popularity_category'] = pd.cut(
            data[review_column],
            bins=[-1, 100, 1000, 10000, float('inf')],
            labels=['nicho', 'moderado', 'popular', 'muito_popular']
        )
        
        print("\nDistribuição de categorias de popularidade:")
        print(data['popularity_category'].value_counts().sort_index())
        
        return data
    
    def create_score_category(self, data, score_column='positive_ratio'):
        """
        Cria categorias de avaliação baseada no percentual positivo.
        
        Parâmetros:
        - data: DataFrame com os dados
        - score_column: Nome da coluna de score (0-100 ou 0-1)
        
        Retorna:
        - data: DataFrame com nova coluna 'score_category'
        """
        import pandas as pd
        
        data = data.copy()
        
        # Normaliza para 0-100 se necessário
        max_val = data[score_column].max()
        if max_val <= 1:
            normalized = data[score_column] * 100
        else:
            normalized = data[score_column]
        
        data['score_category'] = pd.cut(
            normalized,
            bins=[-1, 40, 70, 85, 100],
            labels=['negativo', 'misto', 'positivo', 'muito_positivo']
        )
        
        print("\nDistribuição de categorias de score:")
        print(data['score_category'].value_counts().sort_index())
        
        return data
    
    def plot_comparison(self, comparison_table, title="Comparação de Divisões"):
        """
        Gera visualização gráfica da comparação estratificada vs aleatória.
        
        Parâmetros:
        - comparison_table: DataFrame retornado por table_stratifiedxrandom
        - title: Título do gráfico
        
        Retorna:
        - None: Exibe o gráfico
        """
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Gráfico 1: Comparação de proporções
        comparison_table[['OVERALL', 'RANDOM', 'STRATIFIED']].plot(
            kind='bar',
            ax=ax1,
            rot=45
        )
        ax1.set_title(f'{title}\nProporções')
        ax1.set_ylabel('Proporção')
        ax1.legend(loc='best')
        ax1.grid(axis='y', alpha=0.3)
        
        # Gráfico 2: Erros percentuais
        comparison_table[['RAND. %ERROR', 'STRAT. %ERROR']].plot(
            kind='bar',
            ax=ax2,
            rot=45,
            color=['orange', 'green']
        )
        ax2.set_title(f'{title}\nErros Percentuais')
        ax2.set_ylabel('Erro %')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.legend(loc='best')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def calculate_split_quality_metrics(self, comparison_table):
        """
        Calcula métricas de qualidade da divisão dos dados.
        
        Parâmetros:
        - comparison_table: DataFrame retornado por table_stratifiedxrandom
        
        Retorna:
        - dict: Dicionário com métricas de qualidade
        """
        
        metrics = {}
        
        # Desvio padrão dos erros
        metrics['random_error_std'] = comparison_table['RAND. %ERROR'].std()
        metrics['stratified_error_std'] = comparison_table['STRAT. %ERROR'].std()
        
        # Erro absoluto médio
        metrics['random_mae'] = comparison_table['RAND. %ERROR'].abs().mean()
        metrics['stratified_mae'] = comparison_table['STRAT. %ERROR'].abs().mean()
        
        # Erro máximo
        metrics['random_max_error'] = comparison_table['RAND. %ERROR'].abs().max()
        metrics['stratified_max_error'] = comparison_table['STRAT. %ERROR'].abs().max()
        
        # Score de qualidade (quanto menor o erro, melhor)
        metrics['random_quality_score'] = 100 - metrics['random_mae']
        metrics['stratified_quality_score'] = 100 - metrics['stratified_mae']
        
        # Imprime métricas
        print("\n" + "="*80)
        print("MÉTRICAS DE QUALIDADE DA DIVISÃO")
        print("="*80)
        print("\nDIVISÃO ALEATÓRIA:")
        print(f"  Desvio Padrão dos Erros: {metrics['random_error_std']:.2f}%")
        print(f"  Erro Absoluto Médio: {metrics['random_mae']:.2f}%")
        print(f"  Erro Máximo: {metrics['random_max_error']:.2f}%")
        print(f"  Score de Qualidade: {metrics['random_quality_score']:.2f}/100")
        
        print("\nDIVISÃO ESTRATIFICADA:")
        print(f"  Desvio Padrão dos Erros: {metrics['stratified_error_std']:.2f}%")
        print(f"  Erro Absoluto Médio: {metrics['stratified_mae']:.2f}%")
        print(f"  Erro Máximo: {metrics['stratified_max_error']:.2f}%")
        print(f"  Score de Qualidade: {metrics['stratified_quality_score']:.2f}/100")
        
        improvement = metrics['random_mae'] - metrics['stratified_mae']
        print(f"\n✓ MELHORIA COM ESTRATIFICAÇÃO: {improvement:.2f}% de redução no erro")
        print("="*80)
        
        return metrics
    
    def recommend_split_method(self, data, column, test_ratio=0.2):
        """
        Recomenda automaticamente o melhor método de divisão baseado nos dados.
        
        Parâmetros:
        - data: DataFrame com os dados
        - column: Coluna para análise
        - test_ratio: Proporção de teste
        
        Retorna:
        - str: Recomendação do método
        """
        
        # Análise da distribuição
        value_counts = data[column].value_counts()
        n_categories = len(value_counts)
        min_category_size = value_counts.min()
        max_category_size = value_counts.max()
        imbalance_ratio = max_category_size / min_category_size if min_category_size > 0 else float('inf')
        
        print("\n" + "="*80)
        print("ANÁLISE E RECOMENDAÇÃO DE MÉTODO DE DIVISÃO")
        print("="*80)
        print(f"\nColuna analisada: {column}")
        print(f"Número de categorias: {n_categories}")
        print(f"Menor categoria: {min_category_size} amostras")
        print(f"Maior categoria: {max_category_size} amostras")
        print(f"Razão de desbalanceamento: {imbalance_ratio:.2f}x")
        
        # Critérios de decisão
        recommendation = ""
        
        if n_categories < 2:
            recommendation = "DIVISÃO ALEATÓRIA SIMPLES"
            reason = "Apenas uma categoria detectada - estratificação não aplicável"
        elif min_category_size < 2:
            recommendation = "DIVISÃO ALEATÓRIA SIMPLES"
            reason = "Categorias com muito poucas amostras para estratificação"
        elif imbalance_ratio > 100:
            recommendation = "DIVISÃO ESTRATIFICADA (CRÍTICO)"
            reason = f"Alto desbalanceamento ({imbalance_ratio:.0f}x) - estratificação essencial"
        elif imbalance_ratio > 10:
            recommendation = "DIVISÃO ESTRATIFICADA (RECOMENDADO)"
            reason = f"Desbalanceamento moderado ({imbalance_ratio:.0f}x) - estratificação recomendada"
        elif n_categories > 10:
            recommendation = "DIVISÃO ALEATÓRIA ou AGRUPAR CATEGORIAS"
            reason = "Muitas categorias - considere agrupar antes de estratificar"
        else:
            recommendation = "DIVISÃO ESTRATIFICADA (OPCIONAL)"
            reason = "Distribuição relativamente balanceada - ambos os métodos são viáveis"
        
        print(f"\n{'🎯 RECOMENDAÇÃO'}: {recommendation}")
        print(f"Motivo: {reason}")
        print("="*80)
        
        return recommendation
    
    def full_analysis(self, data, column, test_ratio=0.2, plot=True):
        """
        Executa análise completa: recomendação + comparação + métricas + visualização.
        
        Parâmetros:
        - data: DataFrame com os dados
        - column: Coluna para estratificação
        - test_ratio: Proporção de teste
        - plot: Se True, gera visualização gráfica
        
        Retorna:
        - dict: Resultados completos da análise
        """
        results = {}
        
        # 1. Recomendação
        results['recommendation'] = self.recommend_split_method(data, column, test_ratio)
        
        # 2. Comparação
        results['comparison_table'] = self.table_stratifiedxrandom(data, column, test_ratio)
        
        # 3. Métricas
        results['metrics'] = self.calculate_split_quality_metrics(results['comparison_table'])
        
        # 4. Visualização
        if plot:
            try:
                self.plot_comparison(results['comparison_table'], title=f"Coluna: {column}")
            except Exception as e:
                print(f"\n⚠ Não foi possível gerar o gráfico: {e}")
        
        return results