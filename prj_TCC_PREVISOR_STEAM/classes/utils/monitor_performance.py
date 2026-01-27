"""
Monitor de Performance do Banco de Dados

Este script analisa os logs para identificar:
- Queries lentas (acima de 1 segundo)
- Queries mais frequentes
- Estatísticas de uso do banco

Para executar:
    python -m prj_TCC_PREVISOR_STEAM.classes.utils.monitor_performance
"""

import re
import logging
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from prj_TCC_PREVISOR_STEAM.classes.data.database import Database

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor de performance de queries do banco de dados."""
    
    # Threshold para queries lentas (em segundos)
    CON_SLOW_QUERY_THRESHOLD = 1.0
    
    def __init__(self):
        """Inicializa o monitor."""
        self.var_listSlowQueries = []
        self.var_dictQueryStats = defaultdict(list)
        self.var_objOperationCounts = Counter()
    
    def analisar_logs(self, arg_strLogPath: str = None) -> Dict:
        """
        Analisa arquivo de log para extrair métricas de performance.
        
        Args:
            arg_strLogPath: Caminho para arquivo de log. Se None, usa log padrão.
        
        Returns:
            Dicionário com estatísticas de performance
        """
        if arg_strLogPath is None:
            # Usa diretório padrão de logs
            var_pathLog = Path("prj_TCC_PREVISOR_STEAM/resources/logs")
            if not var_pathLog.exists():
                logger.warning(f"Diretório de logs não encontrado: {var_pathLog}")
                return {}
            
            # Busca arquivo de log mais recente
            var_listLogFiles = list(var_pathLog.glob("*.log"))
            if not var_listLogFiles:
                logger.warning("Nenhum arquivo de log encontrado")
                return {}
            
            arg_strLogPath = str(max(var_listLogFiles, key=lambda p: p.stat().st_mtime))
        
        logger.info(f"Analisando log: {arg_strLogPath}")
        
        # Regex para capturar logs de performance
        # Formato: "[SLOW QUERY] Query executada em 1.23s: SELECT ..."
        var_patternSlowQuery = re.compile(
            r'\[SLOW QUERY\] Query executada em ([\d.]+)s: (.+?)(?:\n|$)',
            re.MULTILINE
        )
        
        var_patternQuery = re.compile(
            r'Query executada em ([\d.]+)s: (.+?)(?:\n|$)',
            re.MULTILINE
        )
        
        try:
            with open(arg_strLogPath, 'r', encoding='utf-8') as f:
                var_strContent = f.read()
            
            # Encontra queries lentas
            for var_match in var_patternSlowQuery.finditer(var_strContent):
                var_floatDuracao = float(var_match.group(1))
                var_strQuery = var_match.group(2).strip()
                
                self.var_listSlowQueries.append({
                    'duracao': var_floatDuracao,
                    'query': var_strQuery,
                    'tipo': self._identificar_tipo_query(var_strQuery)
                })
            
            # Encontra todas as queries
            for var_match in var_patternQuery.finditer(var_strContent):
                var_floatDuracao = float(var_match.group(1))
                var_strQuery = var_match.group(2).strip()
                var_strTipo = self._identificar_tipo_query(var_strQuery)
                
                self.var_dictQueryStats[var_strTipo].append(var_floatDuracao)
                self.var_objOperationCounts[var_strTipo] += 1
            
            logger.info(f"Análise completa - {len(self.var_listSlowQueries)} queries lentas encontradas")
            
            return self._gerar_relatorio()
        
        except Exception as e:
            logger.error(f"Erro ao analisar log: {e}")
            return {}
    
    def _identificar_tipo_query(self, arg_strQuery: str) -> str:
        """
        Identifica tipo de query (SELECT, INSERT, UPDATE, DELETE, etc).
        
        Args:
            arg_strQuery: Query SQL
        
        Returns:
            Tipo da query
        """
        var_strQuery = arg_strQuery.strip().upper()
        
        if var_strQuery.startswith('SELECT'):
            # Verifica se é COUNT
            if 'COUNT(' in var_strQuery:
                return 'SELECT COUNT'
            # Verifica se tem JOIN
            elif 'JOIN' in var_strQuery:
                return 'SELECT JOIN'
            else:
                return 'SELECT'
        elif var_strQuery.startswith('INSERT'):
            return 'INSERT'
        elif var_strQuery.startswith('UPDATE'):
            return 'UPDATE'
        elif var_strQuery.startswith('DELETE'):
            return 'DELETE'
        elif var_strQuery.startswith('CREATE'):
            return 'CREATE'
        else:
            return 'OTHER'
    
    def _gerar_relatorio(self) -> Dict:
        """
        Gera relatório de performance.
        
        Returns:
            Dicionário com estatísticas
        """
        var_dictStats = {
            'slow_queries': len(self.var_listSlowQueries),
            'total_queries': sum(self.var_objOperationCounts.values()),
            'por_tipo': {},
            'top_slow_queries': sorted(
                self.var_listSlowQueries,
                key=lambda x: x['duracao'],
                reverse=True
            )[:10]  # Top 10 queries mais lentas
        }
        
        # Estatísticas por tipo de query
        for var_strTipo, var_listDuracoes in self.var_dictQueryStats.items():
            if var_listDuracoes:
                var_dictStats['por_tipo'][var_strTipo] = {
                    'total': len(var_listDuracoes),
                    'media': sum(var_listDuracoes) / len(var_listDuracoes),
                    'max': max(var_listDuracoes),
                    'min': min(var_listDuracoes)
                }
        
        return var_dictStats
    
    def imprimir_relatorio(self, arg_dictStats: Dict):
        """
        Imprime relatório formatado no console.
        
        Args:
            arg_dictStats: Dicionário com estatísticas
        """
        print("\n" + "=" * 80)
        print("RELATÓRIO DE PERFORMANCE DO BANCO DE DADOS")
        print("=" * 80)
        
        print(f"\nRESUMO:")
        print(f"  Total de queries: {arg_dictStats['total_queries']}")
        print(f"  Queries lentas (>{self.SLOW_QUERY_THRESHOLD}s): {arg_dictStats['slow_queries']}")
        
        if arg_dictStats['por_tipo']:
            print(f"\nESTATÍSTICAS POR TIPO:")
            for var_strTipo, var_dictInfo in arg_dictStats['por_tipo'].items():
                print(f"\n  {var_strTipo}:")
                print(f"    Total: {var_dictInfo['total']}")
                print(f"    Média: {var_dictInfo['media']:.3f}s")
                print(f"    Máximo: {var_dictInfo['max']:.3f}s")
                print(f"    Mínimo: {var_dictInfo['min']:.3f}s")
        
        if arg_dictStats['top_slow_queries']:
            print(f"\nTOP 10 QUERIES MAIS LENTAS:")
            for i, var_dictQuery in enumerate(arg_dictStats['top_slow_queries'], 1):
                print(f"\n  {i}. {var_dictQuery['duracao']:.3f}s - {var_dictQuery['tipo']}")
                # Trunca query para 100 caracteres
                var_strQueryShort = var_dictQuery['query'][:100]
                if len(var_dictQuery['query']) > 100:
                    var_strQueryShort += "..."
                print(f"     {var_strQueryShort}")
        
        print("\n" + "=" * 80)
    
    def obter_stats_tabelas(self) -> Dict:
        """
        Obtém estatísticas atuais das tabelas do banco.
        
        Returns:
            Dicionário com estatísticas de tabelas
        """
        try:
            var_dictStats = Database.obter_stats_tabelas()
            
            print("\n" + "=" * 80)
            print("ESTATÍSTICAS DAS TABELAS")
            print("=" * 80)
            
            for var_strTabela, var_dictInfo in var_dictStats.items():
                print(f"\n  {var_strTabela}:")
                print(f"    Registros: {var_dictInfo['rows']:,}")
                print(f"    Tamanho: {var_dictInfo['size']}")
            
            print("\n" + "=" * 80)
            
            return var_dictStats
        
        except Exception as e:
            logger.error(f"Erro ao obter stats de tabelas: {e}")
            return {}
    
    def sugerir_otimizacoes(self):
        """Sugere otimizações baseadas nas queries lentas encontradas."""
        print("\n" + "=" * 80)
        print("SUGESTÕES DE OTIMIZAÇÃO")
        print("=" * 80)
        
        if not self.var_listSlowQueries:
            print("\n  Nenhuma query lenta detectada! Sistema está performático.")
            print("=" * 80)
            return
        
        # Analisa padrões de queries lentas
        var_dictTiposLentos = Counter([q['tipo'] for q in self.var_listSlowQueries])
        
        print("\nQueries lentas por tipo:")
        for var_strTipo, var_intCount in var_dictTiposLentos.most_common():
            print(f"  - {var_strTipo}: {var_intCount} queries")
        
        print("\nRecomendações:")
        
        if var_dictTiposLentos.get('SELECT COUNT', 0) > 0:
            print("\n  1. SELECT COUNT lentos:")
            print("     - Considere criar índices nas colunas filtradas")
            print("     - Use approximate counts para tabelas grandes (SELECT reltuples FROM pg_class)")
            print("     - Execute: Database.criar_indices_performance()")
        
        if var_dictTiposLentos.get('SELECT JOIN', 0) > 0:
            print("\n  2. SELECT com JOIN lentos:")
            print("     - Verifique índices nas colunas de join")
            print("     - Considere materialized views para joins frequentes")
            print("     - Analise plano de execução: EXPLAIN ANALYZE <query>")
        
        if var_dictTiposLentos.get('SELECT', 0) > 0:
            print("\n  3. SELECT genéricos lentos:")
            print("     - Revise colunas selecionadas (evite SELECT *)")
            print("     - Adicione índices em colunas de WHERE e ORDER BY")
            print("     - Execute: Database.analisar_tabelas()")
        
        print("\n  4. Geral:")
        print("     - Execute ANALYZE regularmente: Database.analisar_tabelas()")
        print("     - Monitore estatísticas: Database.obter_stats_tabelas()")
        print("     - Implemente connection pooling para produção:")
        print("       Database.inicializar_pool(min_connections=2, max_connections=10)")
        
        print("\n" + "=" * 80)


def main():
    """Função principal."""
    logger.info("Iniciando monitoramento de performance...")
    
    var_objMonitor = PerformanceMonitor()
    
    # Analisa logs
    var_dictStats = var_objMonitor.analisar_logs()
    
    if var_dictStats:
        var_objMonitor.imprimir_relatorio(var_dictStats)
    
    # Obtém estatísticas atuais do banco
    var_objMonitor.obter_stats_tabelas()
    
    # Sugere otimizações
    var_objMonitor.sugerir_otimizacoes()
    
    logger.info("Monitoramento concluído!")


if __name__ == "__main__":
    main()
