from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL

import logging

logger = logging.getLogger(__name__)

class PostgreSQLCheckpoint(PostgreSQL):
    """
    Classe para operações com PostgreSQL.
    """
    
    @classmethod
    def salvar_checkpoint(cls, arg_intPcId: int, arg_intUltimoIndice: int, arg_strTipo: str = "STEAM"):
        """
        Salva checkpoint do progresso de processamento.
        
        Parâmetros:
        - arg_intPcId: ID do PC processando
        - arg_intUltimoIndice: Último índice processado com sucesso
        - arg_strTipo: Tipo de processamento (STEAM ou ITAD)
        """
        var_connConnection = cls.conectar()
        try:
            var_strSQL = """
            INSERT INTO processing_checkpoint (pc_id, ultimo_indice, tipo_processamento, timestamp)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (pc_id, tipo_processamento) DO UPDATE SET
                ultimo_indice = EXCLUDED.ultimo_indice,
                timestamp = EXCLUDED.timestamp;
            """
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_intPcId, arg_intUltimoIndice, arg_strTipo))
                var_connConnection.commit()
                logger.info(f"Checkpoint salvo: PC {arg_intPcId}, índice {arg_intUltimoIndice:,}, tipo {arg_strTipo}")
        except Exception as e:
            logger.warning(f"Erro ao salvar checkpoint (tabela pode não existir): {e}")
            var_connConnection.rollback()
        finally:
            cls.desconectar(var_connConnection)
    
    @classmethod
    def recuperar_checkpoint(cls, arg_intPcId: int, arg_strTipo: str = "STEAM") -> int:
        """
        Recupera último checkpoint salvo para continuar processamento.
        
        Parâmetros:
        - arg_intPcId: ID do PC
        - arg_strTipo: Tipo de processamento (STEAM ou ITAD)
        
        Retorna:
        - int: Último índice processado ou 0 se não houver checkpoint
        """
        var_connConnection = cls.conectar()
        try:
            var_strSQL = """
            SELECT ultimo_indice FROM processing_checkpoint
            WHERE pc_id = %s AND tipo_processamento = %s;
            """
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_intPcId, arg_strTipo))
                var_listResult = cursor.fetchone()
                
                if var_listResult:
                    var_intIndice = var_listResult[0]
                    logger.info(f"Checkpoint recuperado: PC {arg_intPcId}, índice {var_intIndice:,}, tipo {arg_strTipo}")
                    return var_intIndice
                else:
                    logger.info(f"Nenhum checkpoint encontrado para PC {arg_intPcId}, tipo {arg_strTipo}")
                    return 0
        except Exception as e:
            logger.warning(f"Erro ao recuperar checkpoint (iniciando do zero): {e}")
            return 0
        finally:
            cls.desconectar(var_connConnection)
    
    @classmethod
    def limpar_checkpoint(cls, arg_intPcId: int, arg_strTipo: str = "STEAM"):
        """
        Limpa checkpoint após conclusão bem-sucedida do processamento.
        
        Parâmetros:
        - arg_intPcId: ID do PC
        - arg_strTipo: Tipo de processamento
        """
        var_connConnection = cls.conectar()
        try:
            var_strSQL = "DELETE FROM processing_checkpoint WHERE pc_id = %s AND tipo_processamento = %s;"
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_intPcId, arg_strTipo))
                var_connConnection.commit()
                logger.info(f"Checkpoint limpo: PC {arg_intPcId}, tipo {arg_strTipo}")
        except Exception as e:
            logger.warning(f"Erro ao limpar checkpoint: {e}")
            var_connConnection.rollback()
        finally:
            cls.desconectar(var_connConnection)