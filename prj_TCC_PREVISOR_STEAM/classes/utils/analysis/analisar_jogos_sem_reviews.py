"""
Script para analisar jogos sem reviews e decidir estratégia de processamento.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()


def analisar_situacao_reviews():
    """
    Analisa a situação de reviews nos dados coletados.
    """
    try:
        # Nota: Este script foi modernizado para usar PostgreSQL local
        # Em caso de uso, atualizar para usar repositório PostgreSQL
        logger.warning("Script requer atualização para usar PostgreSQL local em vez de Supabase")
        
        # TODO: Implementar conexão com PostgreSQL local
        logger.info("Carregando dados da steam_raw...")
        var_listTodosDados = []
        
        var_intTotal = len(var_listTodosDados)
        var_intComDetalhes = 0
        var_intComReviews = 0
        var_intReviewsZeradas = 0
        var_intCompletosSemReviews = 0
        var_intIncompletos = 0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"ANÁLISE DE REVIEWS - Total de registros: {var_intTotal:,}")
        logger.info(f"{'='*60}\n")
        
        for var_dictDado in var_listTodosDados:
            var_boolTemDetalhes = var_dictDado.get("detalhes") is not None
            var_boolTemReviews = var_dictDado.get("reviews") is not None
            
            if var_boolTemDetalhes:
                var_intComDetalhes += 1
                
                if var_boolTemReviews:
                    var_intComReviews += 1
                    
                    # Verifica se tem reviews zeradas
                    var_dictReviews = var_dictDado.get("reviews")
                    if isinstance(var_dictReviews, dict):
                        var_intTotalReviews = var_dictReviews.get("total_reviews", 0)
                        if var_intTotalReviews == 0:
                            var_intReviewsZeradas += 1
                else:
                    var_intCompletosSemReviews += 1
            else:
                var_intIncompletos += 1
        
        # Relatório
        print(f"\n{'='*60}")
        print(f"RELATÓRIO DE REVIEWS")
        print(f"{'='*60}")
        print(f"\n📊 VISÃO GERAL:")
        print(f"   Total de registros: {var_intTotal:,}")
        print(f"\n✅ DADOS COMPLETOS:")
        print(f"   Com detalhes: {var_intComDetalhes:,} ({var_intComDetalhes/var_intTotal:.1%})")
        print(f"   Com reviews: {var_intComReviews:,} ({var_intComReviews/var_intTotal:.1%})")
        print(f"\n⚠️  PROBLEMAS DE REVIEWS:")
        print(f"   Detalhes OK mas SEM reviews: {var_intCompletosSemReviews:,} ({var_intCompletosSemReviews/var_intTotal:.1%})")
        print(f"   Reviews zeradas (0 avaliações): {var_intReviewsZeradas:,} ({var_intReviewsZeradas/var_intComReviews:.1%} das com reviews)")
        print(f"\n❌ DADOS INCOMPLETOS:")
        print(f"   Sem detalhes: {var_intIncompletos:,} ({var_intIncompletos/var_intTotal:.1%})")
        
        print(f"\n{'='*60}")
        print(f"RECOMENDAÇÕES:")
        print(f"{'='*60}")
        
        var_floatTaxaSemReviews = var_intCompletosSemReviews / var_intComDetalhes if var_intComDetalhes > 0 else 0
        
        if var_floatTaxaSemReviews > 0.5:
            print(f"\n🔴 CRÍTICO: {var_floatTaxaSemReviews:.1%} dos jogos com detalhes não têm reviews!")
            print(f"   → Recomendação: ATIVAR processamento sem reviews obrigatórios")
            print(f"   → Use: buscar_jogos_incompletos(arg_boolRequererReviews=False)")
            print(f"   → Jogos sem reviews terão valores padrão (0 avaliações)")
        elif var_floatTaxaSemReviews > 0.3:
            print(f"\n🟡 ATENÇÃO: {var_floatTaxaSemReviews:.1%} dos jogos não têm reviews")
            print(f"   → Considere processar mesmo sem reviews")
            print(f"   → Você perderá {var_intCompletosSemReviews:,} jogos se reviews forem obrigatórios")
        else:
            print(f"\n🟢 OK: Apenas {var_floatTaxaSemReviews:.1%} sem reviews")
            print(f"   → Pode manter reviews como obrigatórios se desejar")
        
        print(f"\n{'='*60}")
        print(f"EXEMPLO DE USO (COM POSTGRESQL LOCAL):")
        print(f"{'='*60}")
        print(f"\n# Atualizar este script para usar PostgreSQL:")
        print(f"from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL")
        print(f"dados = PostgreSQL.buscar_dados(consulta_sql)")
        print(f"\n{'='*60}\n")
        
        # Desconecta
        logger.info("Análise concluída")
        
    except Exception as e:
        logger.error(f"Erro ao analisar reviews: {e}")
        raise


if __name__ == "__main__":
    analisar_situacao_reviews()
