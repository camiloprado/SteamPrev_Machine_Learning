from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam

import logging

logger = logging.getLogger(__name__)

class LimparGenero:
    """
    Classe responsável por limpar e padronizar o campo "genero" dos jogos.
    """
    _var_setGenerosNormalizados = None
    _var_setIdGeneros = None
    
    @classmethod
    def _inserir_novos_generos(cls, arg_dictNovosGeneros: dict[int, str]) -> list[str]:
        """
        Processa e normaliza gêneros de steam_raw, inserindo novos na tabela steam_generos.
        
        Parâmetros:
        - arg_dictNovosGeneros (dict[int, str]): Dicionário de gêneros novos a serem inseridos.

        Retorna:
        - list[str]: Conjunto de gêneros normalizados
        """
        try:
            logger.info("Inserindo novos gêneros no banco...")
            var_connConnection = PostgreSQL.conectar()
            arg_dictNovosGeneros = {idx: nome for idx, nome in enumerate(arg_dictNovosGeneros, start=1)}
            var_listValores = [(idx, nome) for idx, nome in arg_dictNovosGeneros.items()]

            # Insere usando execute_values para performance
            from psycopg2.extras import execute_values
            var_strSQLInsert = """
                INSERT INTO public.steam_generos (id_genero, nome_genero)
                VALUES %s
                ON CONFLICT (id_genero) DO NOTHING
            """
            
            with var_connConnection.cursor() as cursor:
                execute_values(cursor, var_strSQLInsert, var_listValores)
                var_connConnection.commit()
            
            logger.info(f"{len(arg_dictNovosGeneros)} gêneros inseridos com sucesso")
            
            # Log dos novos gêneros
            logger.info("Novos gêneros adicionados:")
            for _, nome in var_listValores[:20]:  # Mostra apenas as primeiras 20
                logger.info(f"  • {nome}")
            if len(var_listValores) > 20:
                logger.info(f"  ... e mais {len(var_listValores) - 20} gêneros")
            
            cls._var_setGenerosNormalizados.update(arg_dictNovosGeneros.values())

        except Exception as e:
            if var_connConnection:
                var_connConnection.rollback()
            logger.error(f"Erro ao inserir novos gêneros: {e}")
            raise Exception(f"Erro ao inserir novos gêneros: {e}")
        finally:
            if var_connConnection:
                PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def processar_genero_completo(cls, arg_listGeneros: list[dict[int, str]]) -> list[str]:
        """
        Processa e normaliza gêneros de steam_raw, inserindo novos na tabela steam_generos.
        
        Parâmetros:
        - arg_listGeneros (list[dict[int, str]]): Lista de dicionários representando gêneros do campo 'genres' do steam_raw.

        Retorna:
        - list[str]: Conjunto de gêneros normalizados
        """
        try:
            cls._var_setIdGeneros = set()
            
            var_listIdGeneros = []
            var_dictGeneros = {}
            for var_dictGenero in arg_listGeneros:
                var_listIdGeneros.append(int(var_dictGenero.get("id", None)))
                var_dictGeneros[var_dictGenero.get("id", None)] = var_dictGenero.get("description", None)

            cls._var_setIdGeneros.update(var_listIdGeneros)
            
            # Identifica gêneros que ainda não existem no BD
            var_dictGenerosExistentes = PostgreSQLSteam.buscar_dados_genero()
            
            var_dictNovosGeneros = {}
            for var_intId in cls._var_setIdGeneros:
                if var_intId not in var_dictGenerosExistentes:
                    var_dictNovosGeneros[var_intId] = var_dictGeneros.get(var_intId, None)

            # Insere novos gêneros no banco
            if var_dictNovosGeneros:
                # Dicionário de tradução e normalização
                var_dictTraducao = cls._obter_dicionario_traducao_generos()
                
                for var_strGenero in cls._var_setGenerosNormalizados:
                    var_strNomeNormalizado = cls._normalizar_genero(var_strGenero, var_dictTraducao)
                    if var_strNomeNormalizado:
                        cls._var_setGenerosNormalizados.add(var_strNomeNormalizado)
                cls._inserir_novos_generos(var_dictNovosGeneros)
            
            return list(cls._var_setIdGeneros)
            
        except Exception as e:
            logger.error(f"Erro no processamento de gêneros: {e}")
            raise
        
    @staticmethod
    def _normalizar_genero(arg_strNome: str, arg_dictTraducao: dict[str, str]) -> str:
        """
        Normaliza nome de gênero usando dicionário de tradução.
        
        Parâmetros:
        - arg_strNome: Nome do gênero bruto
        - arg_dictTraducao: Dicionário de padrões -> nome normalizado
        
        Retorna:
        - str: Nome normalizado ou None se inválido
        """
        if not arg_strNome or len(arg_strNome) < 2:
            return None
        
        var_strNomeLower = arg_strNome.lower()
        
        # Verifica correspondência com padrões do dicionário
        for var_dictPadroes, var_strNomeNormalizado in arg_dictTraducao.items():
            for var_strPadrao in var_dictPadroes:
                if var_strPadrao.lower() in var_strNomeLower:
                    return var_strNomeNormalizado
        
        # Fallback: Capitaliza primeira letra de cada palavra
        return arg_strNome.title()
    
    @staticmethod
    def _obter_dicionario_traducao_generos() -> dict[tuple, str]:
        """
        Retorna dicionário de tradução para normalização de gêneros.
        
        Retorna:
        - dict[tuple, str]: {(padrão1, padrão2, ...): nome_normalizado}
        """
        return {
            # GÊNEROS DE JOGOS PRINCIPAIS (Core Genres)
            ('acao', 'action'): 'Ação',
            ('aventura', 'adventure', 'aventure'): 'Aventura',
            ('rpg',): 'RPG',
            ('estrategia', 'estratgia', 'strategy'): 'Estratégia',
            ('simulacao', 'simulao', 'simulation'): 'Simulação',
            ('corrida', 'racing'): 'Corrida',
            ('esportes',): 'Esportes',
            ('casual',): 'Casual',
            ('indie',): 'Indie',
            ('multijogador massivo',): 'Multijogador Massivo (MMO)',
            
            # MODELOS DE NEGÓCIO E ACESSO
            ('acesso antecipado', 'early access'): 'Acesso Antecipado',
            ('gratuitos para jogar', 'free to play'): 'Gratuito para Jogar',

            # CONTEÚDO ADULTO E SENSÍVEL
            ('conteudo sexual', 'contedo sexual'): 'Conteúdo Sexual',
            ('nudez',): 'Nudez',
            ('violencia', 'violncia'): 'Violência',
            ('violencia detalhada', 'violncia detalhada'): 'Violência Detalhada',

            # SOFTWARE E UTILITÁRIOS (Não-Jogos)
            ('animacao e modelagem', 'animao e modelagem'): 'Animação e Modelagem',
            ('design e ilustracao', 'design e ilustrao'): 'Design e Ilustração',
            ('edicao de fotos', 'edio de fotos'): 'Edição de Fotos',
            ('producao de audio', 'produo de udio'): 'Produção de Áudio',
            ('producao de video', 'produo de vdeo'): 'Produção de Vídeo',
            ('publicacao para web', 'publicao para web'): 'Publicação para Web',
            ('desenvolvimento de jogos',): 'Desenvolvimento de Jogos',
            ('software de treinamento',): 'Software de Treinamento',
            ('utilitarios', 'utilitrios'): 'Utilitários',
            ('contabilidade',): 'Contabilidade',
            ('educacao', 'educao'): 'Educação',

            # VÍDEO E MÍDIA
            ('filme',): 'Filme',
            ('documentario', 'documentrio'): 'Documentário',
            ('episodico', 'episdico'): 'Episódico',
            ('curta',): 'Curta',
            ('tutorial',): 'Tutorial',
            ('video em 360o',): 'Vídeo em 360'
        }
