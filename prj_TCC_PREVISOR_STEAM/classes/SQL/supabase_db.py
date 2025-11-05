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
            raise Exception(f"Erro ao conectar ao Supabase: {e}")
    
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

            # Caso 2: Atualizar apenas REVIEWS (registro já deve existir)
            if var_dictReviews is not None:
                # Busca o registro existente
                var_apiRegistro = cls._var_botClient.table("steam_raw").select("appid").eq("appid", var_intAppid).execute()
                
                if var_apiRegistro.data and len(var_apiRegistro.data) > 0:
                    # Atualiza apenas o campo reviews
                    var_apiResult = cls._var_botClient.table("steam_raw").update({
                        "reviews": var_dictReviews
                    }).eq("appid", var_intAppid).execute()
                else:
                    logger.warning(
                        f"AppID {var_intAppid} não encontrado. "
                        f"Insira os detalhes primeiro antes de adicionar reviews."
                    )
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_raw: {e}")
            raise Exception(f"Erro ao inserir dados steam_raw: {e}")
    
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
            raise Exception(f"Erro ao buscar dados steam_raw: {e}")
    
    @classmethod
    def buscar_todos_dadosSteamRaw(cls, arg_intLimit: int = None) -> List[Dict[str, Any]]:
        """
        Busca todos os jogos da tabela steam_raw.
        
        Parâmetros:
        - arg_intLimit (int): Número máximo de registros. Se None, busca todos com paginação. (padrão: None)
            
        Retorna:
        - Lista de dicionários com os dados
        """
        cls._garantir_conexao()
        
        try:
            if arg_intLimit is not None:
                # Com limite específico
                var_apiResult = cls._var_botClient.table("steam_raw").select("*").limit(arg_intLimit).execute()
                return var_apiResult.data if var_apiResult.data else []
            else:
                # Sem limite - busca todos com paginação
                var_listTodosDados = []
                var_intOffset = 0
                var_intPageSize = 1000  # Tamanho da página
                
                while True:
                    var_apiResult = cls._var_botClient.table("steam_raw").select("*").range(
                        var_intOffset, var_intOffset + var_intPageSize - 1
                    ).execute()
                    
                    if not var_apiResult.data or len(var_apiResult.data) == 0:
                        break
                    
                    var_listTodosDados.extend(var_apiResult.data)
                    
                    # Se retornou menos que o page size, chegou no fim
                    if len(var_apiResult.data) < var_intPageSize:
                        break
                    
                    var_intOffset += var_intPageSize
                
                logger.info(f"Total de registros carregados de steam_raw: {len(var_listTodosDados)}")
                return var_listTodosDados

        except Exception as e:
            logger.error(f"Erro ao buscar todos os dados steam_raw: {e}")
            raise Exception(f"Erro ao buscar todos os dados steam_raw: {e}")
    
    # ========== MÉTODOS PARA steam_bd ==========
    
    @classmethod
    def inserir_dadosSteamBD(cls, arg_listDados: list) -> None:
        """
        Insere ou atualiza dados processados na tabela steam_bd.
        
        Parâmetros:
        - arg_listDados (list): Dicionário com os dados processados do jogo
        """
        cls._garantir_conexao()
        
        try:
            for var_dictDados in arg_listDados:
                var_intAppid = var_dictDados.get("appid")
                if not var_intAppid:
                    raise ValueError("appid é obrigatório")

                # Prepara dados para inserção
                var_dictDadosInsert = {
                    "appid": var_intAppid,
                    "nome": var_dictDados.get("nome"),
                    "classificacao_etaria": var_dictDados.get("classificacao_etaria"),
                    "linguagens": var_dictDados.get("linguagens"),
                    "desenvolvedores": var_dictDados.get("desenvolvedores"),
                    "distribuidores": var_dictDados.get("distribuidores"),
                    "preco": var_dictDados.get("preco"),
                    "metacritic_score": var_dictDados.get("metacritic_score"),
                    "categorias": var_dictDados.get("categorias"),
                    "genero": var_dictDados.get("genero"),
                    "data_lancamento": var_dictDados.get("data_lancamento"),
                    "review_score": var_dictDados.get("review_score"),
                    "total_reviews": var_dictDados.get("total_reviews"),
                    "total_negative": var_dictDados.get("total_negative"),
                    "total_positive": var_dictDados.get("total_positive"),
                    "review_score_desc": var_dictDados.get("review_score_desc"),
                }
                # Upsert: insere se não existe, atualiza se existe
                var_apiResult = cls._var_botClient.table("steam_bd").upsert(
                    var_dictDadosInsert,
                    on_conflict="appid"
                ).execute()

                if not var_apiResult:
                    logger.error(f"Erro ao inserir/atualizar AppID {var_intAppid}: {var_apiResult.error}")
                    continue

            logger.info(f"Dados processados salvos para {len(arg_listDados)} registros.")
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_bd: {e}")
            raise Exception(f"Erro ao inserir dados steam_bd: {e}")
    
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
            raise Exception(f"Erro ao buscar dados steam_bd: {e}")
    
    @classmethod
    def buscar_todos_dadosSteamBD(cls, arg_intLimit: int = None) -> List[Dict[str, Any]]:
        """
        Busca todos os jogos da tabela steam_bd.
        
        Parâmetros:
        - arg_intLimit (int): Número máximo de registros. Se None, busca todos com paginação. (padrão: None)
            
        Retorna:
        - Lista de dicionários com os dados
        """
        cls._garantir_conexao()
        
        try:
            if arg_intLimit is not None:
                # Com limite específico
                var_apiResult = cls._var_botClient.table("steam_bd").select("*").limit(arg_intLimit).execute()
                return var_apiResult.data if var_apiResult.data else []
            else:
                # Sem limite - busca todos com paginação
                var_listTodosDados = []
                var_intOffset = 0
                var_intPageSize = 1000  # Tamanho da página
                
                while True:
                    var_apiResult = cls._var_botClient.table("steam_bd").select("*").range(
                        var_intOffset, var_intOffset + var_intPageSize - 1
                    ).execute()
                    
                    if not var_apiResult.data or len(var_apiResult.data) == 0:
                        break
                    
                    var_listTodosDados.extend(var_apiResult.data)
                    
                    # Se retornou menos que o page size, chegou no fim
                    if len(var_apiResult.data) < var_intPageSize:
                        break
                    
                    var_intOffset += var_intPageSize
                
                logger.info(f"Total de registros carregados de steam_bd: {len(var_listTodosDados)}")
                return var_listTodosDados

        except Exception as e:
            logger.error(f"Erro ao buscar todos os dados steam_bd: {e}")
            raise Exception(f"Erro ao buscar todos os dados steam_bd: {e}")
    
    # ========== MÉTODOS UTILITÁRIOS ==========
    @classmethod
    def buscar_jogos_desatualizados(cls, arg_strNomeTabela: str = "steam_raw", arg_intLimite: int = None) -> List[Dict[str, Any]]:
        """
        Busca jogos na tabela escolhida que não foram atualizados recentemente.
        
        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela ('steam_raw' ou 'steam_bd') (padrão: "steam_raw")
        - arg_intLimite (int): Número máximo de registros a retornar (padrão: None)
            
        Retorna:
        - Lista de jogos desatualizados
        """
        
        cls._garantir_conexao()
        
        try:
            var_intDataLimite = Settings._var_dictSettings.get("dias_atualizacao", 30)
            # Define data de corte, jogos com ultima_atualizacao menor que dias_atualizacao serão retornados
            var_dataCorte = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=var_intDataLimite)
            
            if arg_intLimite is not None:
                # Com limite específico
                var_apiResult = cls._var_botClient.table(arg_strNomeTabela).select("*").lt(
                    "ultima_atualizacao", var_dataCorte.isoformat()
                ).limit(arg_intLimite).execute()
                return var_apiResult.data if var_apiResult.data else []
            else:
                # Sem limite - busca todos com paginação
                var_listTodosDados = []
                var_intOffset = 0
                var_intPageSize = 1000  # Tamanho da página
                
                while True:
                    var_apiResult = cls._var_botClient.table(arg_strNomeTabela).select("*").range(
                        var_intOffset, var_intOffset + var_intPageSize - 1
                    ).lt(
                        "ultima_atualizacao", var_dataCorte.isoformat()
                    ).execute()
                    
                    if not var_apiResult.data or len(var_apiResult.data) == 0:
                        break
                    
                    var_listTodosDados.extend(var_apiResult.data)
                    
                    # Se retornou menos que o page size, chegou no fim
                    if len(var_apiResult.data) < var_intPageSize:
                        break
                    
                    var_intOffset += var_intPageSize

                logger.info(f"Total de registros desatualizados de steam_raw: {len(var_listTodosDados)}")
                return var_listTodosDados
        
        except Exception as e:
            logger.error(f"Erro ao buscar jogos antigos: {e}")
            raise Exception(f"Erro ao buscar jogos antigos: {e}")
        
    @classmethod
    def buscar_jogos_incompletos(cls, arg_boolRequererReviews: bool = False) -> List[Dict[str, Any]]:
        """
        Busca jogos na tabela steam_raw que não possuem detalhes ou (opcionalmente) reviews.
        
        Parâmetros:
        - arg_boolRequererReviews (bool): Se True, considera incompletos apenas jogos sem reviews.
                                          Se False, considera incompletos apenas jogos sem detalhes. (padrão: False)
        
        Retorna:
        - Lista de jogos incompletos
        """
        
        cls._garantir_conexao()
        
        try:
            # Sem limite - busca todos com paginação
            var_listTodosDados = []
            var_intOffset = 0
            var_intPageSize = 1000  # Tamanho da página
            
            while True:
                if arg_boolRequererReviews:
                    # Busca jogos sem detalhes OU sem reviews
                    var_apiResult = cls._var_botClient.table("steam_raw").select("*").range(
                        var_intOffset, var_intOffset + var_intPageSize - 1
                    ).or_(
                        "detalhes.is.null,reviews.is.null"
                    ).execute()
                else:
                    # Busca apenas jogos sem detalhes (reviews opcionais)
                    var_apiResult = cls._var_botClient.table("steam_raw").select("*").range(
                        var_intOffset, var_intOffset + var_intPageSize - 1
                    ).is_(
                        "detalhes", "null"
                    ).execute()
                
                if not var_apiResult.data or len(var_apiResult.data) == 0:
                    break
                
                var_listTodosDados.extend(var_apiResult.data)
                
                # Se retornou menos que o page size, chegou no fim
                if len(var_apiResult.data) < var_intPageSize:
                    break
                
                var_intOffset += var_intPageSize

            logger.info(f"Total de registros incompletos de 'steam_raw': {len(var_listTodosDados)} (reviews {'obrigatórios' if arg_boolRequererReviews else 'opcionais'})")
            return var_listTodosDados
            
        except Exception as e:
            logger.error(f"Erro ao buscar jogos incompletos: {e}")
            raise Exception(f"Erro ao buscar jogos incompletos: {e}")
    
    @classmethod
    def buscar_jogos_por_ID(cls, arg_listAppIDs: List[int], arg_strNomeTabel: str = 'steam_raw') -> List[Dict[str, Any]]:
        """
        Busca jogos por uma lista de AppIDs.
        
        Parâmetros:
        - arg_listAppIDs (List[int]): Lista de IDs dos aplicativos Steam
        - arg_strNomeTabel (str): Nome da tabela ('steam_raw' ou 'steam_bd') (padrão: 'steam_raw')
            
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
            raise Exception(f"Erro ao buscar jogos por AppIDs: {e}")

    @classmethod
    def buscar_jogos_por_nome(cls, arg_strNome: str, arg_strNomeTabela: str = "steam_bd") -> List[Dict[str, Any]]:
        """
        Busca jogos por nome (pesquisa parcial, case-insensitive).
        
        Parâmetros:
        - arg_strNome (str): Nome ou parte do nome do jogo
        - arg_strNomeTabela (str): Nome da tabela ('steam_raw' ou 'steam_bd') (padrão: "steam_bd")
            
        Retorna:
        - Lista de jogos encontrados
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table(arg_strNomeTabela).select("*").ilike(
                "nome", f"%{arg_strNome}%"
            ).execute()

            return var_apiResult.data if var_apiResult.data else []

        except Exception as e:
            logger.error(f"Erro ao buscar jogos por nome na tabela {arg_strNomeTabela}: {e}")
            raise Exception(f"Erro ao buscar jogos por nome: {e}")
    
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
            raise Exception(f"Erro ao obter estatísticas: {e}")
    
    @classmethod
    def deletar_jogo(cls, arg_intAppid: int, arg_strTabela: str = "steam_raw") -> bool:
        """
        Deleta um jogo de uma tabela específica.
        
        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam
        - arg_strTabela (str): Nome da tabela ('steam_raw' ou 'steam_bd') (padrão: "steam_raw")

        Retorna:
        - True se deletado com sucesso, False caso contrário
        """
        cls._garantir_conexao()
        
        try:
            var_apiResult = cls._var_botClient.table(arg_strTabela).delete().eq(
                "appid", arg_intAppid
            ).execute()
            
            logger.info(f"AppID {arg_intAppid} deletado de {arg_strTabela}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar jogo: {e}")
            return False
