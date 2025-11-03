from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError(
        "Biblioteca 'supabase' não encontrada. "
        "Instale com: pip install supabase"
    )

logger = logging.getLogger(__name__)


class SupabaseDB:
    """
    Classe para interagir com Supabase usando API REST.
    Compatível com a interface PostgreSQL.
    """
    
    _var_botClient: Optional[Client] = None
    _var_boolConnected: bool = False
    
    @classmethod
    def conectar(cls) -> None:
        """
        Conecta ao Supabase usando as credenciais do .env
        """
        try:
            if cls._var_boolConnected and cls._var_botClient is not None:
                logger.info("Já conectado ao Supabase")
                return
            
            var_strUrl = os.getenv("SUPABASE_URL")
            var_strKey = os.getenv("SUPABASE_KEY")

            if not var_strUrl or not var_strKey:
                raise ValueError(
                    "SUPABASE_URL e SUPABASE_KEY devem estar definidos no .env"
                )

            cls._var_botClient = create_client(var_strUrl, var_strKey)
            cls._var_boolConnected = True
            logger.info("Conectado ao Supabase com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao Supabase: {e}")
            raise
    
    @classmethod
    def desconectar(cls) -> None:
        """
        Desconecta do Supabase (libera recursos)
        """
        if cls._var_boolConnected:
            cls._var_botClient = None
            cls._var_boolConnected = False
            logger.info("Desconectado do Supabase")
    
    @classmethod
    def _garantir_conexao(cls) -> None:
        """
        Garante que existe uma conexão ativa
        """
        if not cls._var_boolConnected or cls._var_botClient is None:
            cls.conectar()
    
    # ========== MÉTODOS PARA steam_raw ==========
    
    @classmethod
    def inserir_dadosSteamRaw(cls, arg_dictDados: Dict[str, Any]) -> None:
        """
        Insere ou atualiza dados na tabela steam_raw.
        
        LÓGICA:
        1. Se tem 'detalhes': INSERT inicial ou UPDATE detalhes
        2. Se tem 'reviews': UPDATE apenas reviews (precisa existir registro)
        
        Parâmetros:
        - arg_dictDados (dict): Dicionário com:
                - appid (obrigatório)
                - detalhes (opcional): dados do jogo
                - reviews (opcional): dados de avaliações
        """
        cls._garantir_conexao()
        
        try:
            var_intAppid = arg_dictDados.get("appid")
            if not var_intAppid:
                raise ValueError("Appid é obrigatório")
            
            var_dictDetalhes = arg_dictDados.get("detalhes")
            var_dictReviews = arg_dictDados.get("reviews")

            # Caso 1: Inserir/atualizar DETALHES
            if var_dictDetalhes is not None:
                var_dictDadosInsert = {
                    "appid": var_intAppid,
                    "detalhes": var_dictDetalhes
                }
                
                # Upsert: insere se não existe, atualiza se existe
                var_apiResult = cls._var_botClient.table("steam_raw").upsert(
                    var_dictDadosInsert,
                    on_conflict="appid"
                ).execute()

                logger.info(f"Detalhes salvos para appid {var_intAppid}")
            
            # Caso 2: Atualizar apenas REVIEWS (registro já deve existir)
            if var_dictReviews is not None:
                # Busca o registro existente
                var_apiRegistro = cls._var_botClient.table("steam_raw").select("appid").eq("appid", var_intAppid).execute()
                
                if var_apiRegistro.data and len(var_apiRegistro.data) > 0:
                    # Atualiza apenas o campo reviews
                    var_apiResult = cls._var_botClient.table("steam_raw").update({
                        "reviews": var_dictReviews
                    }).eq("appid", var_intAppid).execute()

                    logger.info(f"Reviews atualizados para appid {var_intAppid}")
                else:
                    logger.warning(
                        f"AppID {var_intAppid} não encontrado. "
                        f"Insira os detalhes primeiro antes de adicionar reviews."
                    )
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_raw: {e}")
            raise
    
    @classmethod
    def buscar_dadosSteamRaw(cls, arg_intAppid: int) -> Optional[Dict[str, Any]]:
        """
        Busca um jogo específico na tabela steam_raw.
        
        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam
            
        Retorna:
        - Dicionário com os dados ou None se não encontrado
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table("steam_raw").select("*").eq(
                "appid", arg_intAppid
            ).execute()

            if var_apiResult.data and len(var_apiResult.data) > 0:
                return var_apiResult.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados steam_raw: {e}")
            raise
    
    @classmethod
    def buscar_todos_dadosSteamRaw(cls, arg_intLimit: int = 1000) -> List[Dict[str, Any]]:
        """
        Busca todos os jogos da tabela steam_raw.
        
        Parâmetros:
        - arg_intLimit (int): Número máximo de registros (padrão: 1000)
            
        Retorna:
        - Lista de dicionários com os dados
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table("steam_raw").select("*").limit(arg_intLimit).execute()
            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar todos os dados steam_raw: {e}")
            raise
    
    # ========== MÉTODOS PARA steam_bd ==========
    
    @classmethod
    def inserir_dadosSteamBD(cls, arg_dictDados: Dict[str, Any]) -> None:
        """
        Insere ou atualiza dados processados na tabela steam_bd.
        
        Parâmetros:
        - arg_dictDados (dict): Dicionário com os dados processados do jogo
        """
        cls._garantir_conexao()
        
        try:
            var_intAppid = arg_dictDados.get("appid")
            if not var_intAppid:
                raise ValueError("appid é obrigatório")
            
            # Prepara dados para inserção
            var_dictDadosInsert = {
                "appid": var_intAppid,
                "nome": arg_dictDados.get("nome"),
                "data_lancamento": arg_dictDados.get("data_lancamento"),
                "desenvolvedores": arg_dictDados.get("desenvolvedores"),
                "publicadores": arg_dictDados.get("publicadores"),
                "categorias": arg_dictDados.get("categorias"),
                "generos": arg_dictDados.get("generos"),
                "preco_inicial": arg_dictDados.get("preco_inicial"),
                "preco_final": arg_dictDados.get("preco_final"),
                "desconto": arg_dictDados.get("desconto"),
                "avaliacoes_totais": arg_dictDados.get("avaliacoes_totais"),
                "avaliacoes_positivas": arg_dictDados.get("avaliacoes_positivas"),
                "porcentagem_positiva": arg_dictDados.get("porcentagem_positiva"),
                "plataformas": arg_dictDados.get("plataformas")
            }
            
            # Upsert: insere se não existe, atualiza se existe
            var_apiResult = cls._var_botClient.table("steam_bd").upsert(
                var_dictDadosInsert,
                on_conflict="appid"
            ).execute()

            logger.info(f"Dados processados salvos para appid {var_intAppid}")
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_bd: {e}")
            raise
    
    @classmethod
    def buscar_dadosSteamBD(cls, arg_intAppid: int) -> Optional[Dict[str, Any]]:
        """
        Busca um jogo específico na tabela steam_bd.
        
        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam

        Retorna:
        - Dicionário com os dados ou None se não encontrado
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table("steam_bd").select("*").eq(
                "appid", arg_intAppid
            ).execute()

            if var_apiResult.data and len(var_apiResult.data) > 0:
                return var_apiResult.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados steam_bd: {e}")
            raise
    
    @classmethod
    def buscar_todos_dadosSteamBD(cls, arg_intLimit: int = 1000) -> List[Dict[str, Any]]:
        """
        Busca todos os jogos da tabela steam_bd.
        
        Parâmetros:
        - arg_intLimit (int): Número máximo de registros (padrão: 1000)
            
        Retorna:
        - Lista de dicionários com os dados
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table("steam_bd").select("*").limit(arg_intLimit).execute()
            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar todos os dados steam_bd: {e}")
            raise
    
    # ========== MÉTODOS UTILITÁRIOS ==========
    @classmethod
    def buscar_jogos_desatualizados(cls, arg_intLimite: int = 100) -> List[Dict[str, Any]]:
        """
        Busca jogos na tabela steam_raw que não foram atualizados recentemente.
        
        Parâmetros:
        - arg_intLimite (int): Número máximo de registros a retornar (padrão: 100)
            
        Retorna:
        - Lista de jogos desatualizados
        """
        
        cls._garantir_conexao()
        
        try:
            var_intDataLimite = Settings._var_dictSettings.get("dias_atualizacao", 30)
            # Define data de corte, jogos com ultima_atualizacao menor que dias_atualizacao serão retornados
            var_dataCorte = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=var_intDataLimite)
            var_apiResult = cls._var_botClient.table("steam_raw").select("*").lt(
                "ultima_atualizacao", var_dataCorte.isoformat()
            ).limit(arg_intLimite).execute()
            
            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar jogos antigos: {e}")
            raise
        
    @classmethod
    def buscar_jogos_incompletos(cls) -> List[Dict[str, Any]]:
        """
        Busca jogos na tabela steam_raw que não possuem detalhes ou reviews.
        
        Retorna:
        - Lista de jogos incompletos
        """
        
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table("steam_raw").select("*").or_(
                "detalhes.is.null,reviews.is.null"
            ).execute()
            
            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar jogos incompletos: {e}")
            raise
    
    @classmethod
    def buscar_jogos_por_ID(cls, arg_listAppIDs: List[int], arg_strNomeTabel: str = 'steam_raw') -> List[Dict[str, Any]]:
        """
        Busca jogos por uma lista de AppIDs.
        
        Parâmetros:
        - arg_listAppIDs (List[int]): Lista de IDs dos aplicativos Steam
        - arg_strNomeTabel (str): Nome da tabela ('steam_raw' ou 'steam_bd')
            
        Retorna:
        - Lista de jogos encontrados
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table(arg_strNomeTabel).select("*").in_(
                "appid", arg_listAppIDs
            ).execute()

            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar jogos por AppIDs: {e}")
            raise

    @classmethod
    def buscar_jogos_por_nome(cls, arg_strNome: str) -> List[Dict[str, Any]]:
        """
        Busca jogos por nome (pesquisa parcial, case-insensitive).
        
        Parâmetros:
        - arg_strNome (str): Nome ou parte do nome do jogo
            
        Retorna:
        - Lista de jogos encontrados
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table("steam_bd").select("*").ilike(
                "nome", f"%{arg_strNome}%"
            ).execute()

            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar jogos por nome: {e}")
            raise
    
    @classmethod
    def obter_estatisticas(cls) -> Dict[str, int]:
        """
        Obtém estatísticas básicas das tabelas.
        
        Retorna:
        - Dicionário com contagens:
            - total_raw: Total de registros em steam_raw
            - total_bd: Total de registros em steam_bd
            - diferenca: Diferença entre as tabelas
        """
        cls._garantir_conexao()
        
        try:
            # Conta registros em steam_raw
            var_apiResultRaw = cls._var_botClient.table("steam_raw").select(
                "appid", count="exact"
            ).execute()
            var_intTotalRaw = var_apiResultRaw.count if var_apiResultRaw.count else 0

            # Conta registros em steam_bd
            var_apiResultBD = cls._var_botClient.table("steam_bd").select(
                "appid", count="exact"
            ).execute()
            var_intTotalBD = var_apiResultBD.count if var_apiResultBD.count else 0
            
            return {
                "total_raw": var_intTotalRaw,
                "total_bd": var_intTotalBD,
                "diferenca": var_intTotalRaw - var_intTotalBD
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            raise
    
    @classmethod
    def deletar_jogo(cls, arg_intAppid: int, arg_strTabela: str = "steam_raw") -> bool:
        """
        Deleta um jogo de uma tabela específica.
        
        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam
        - arg_strTabela (str): Nome da tabela ('steam_raw' ou 'steam_bd')

        Retorna:
        - True se deletado com sucesso, False caso contrário
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table(arg_strTabela).delete().eq(
                "appid", arg_intAppid
            ).execute()
            
            logger.info(f"Retorna:AppID {arg_intAppid} deletado de {arg_strTabela}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar jogo: {e}")
            return False
