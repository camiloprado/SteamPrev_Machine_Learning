from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam

from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class LimparLinguagens:
    """
    Classe responsável por limpar os dados relacionados às linguagens do banco de dados.
    """
    
    @classmethod
    def normalizar_texto(cls, arg_strTexto: str) -> List[str]:
        """
        Normaliza o texto, removendo acentos, caracteres especiais e convertendo para uma lista de strings.

        Parâmetros:
        - arg_strTexto (str): Texto bruto a ser normalizado.

        Retorna:
        - var_listSeparadas (list): Lista com linguagens normalizadas e separadas
        """
        # Troca quebras de linha e tabs por vírgulas
        var_strTexto = re.sub(r'[\n\r\t]+', ',', arg_strTexto)
        
        # Converte entidades HTML escapadas
        var_strTexto = var_strTexto.replace('&lt;', '<').replace('&gt;', '>')
        
        # Remove tags HTML e BBCode
        var_strTexto = re.sub(r'<[^>]+>|\[[^\]]+\]', '', var_strTexto)
        
        # Destrói frases de interface e anotações intrusivas
        var_strTexto = re.sub(
            r'\**\s*(idiomas? com suporte.*|languages? with full audio.*|Interface:.*|Full Audio:.*|Subtitles:.*|\(Subtitles\))',
            '',
            var_strTexto,
            flags=re.IGNORECASE
        )
        
        # Remove aspas, ponto-e-vírgula, sustenidos e asteriscos
        var_strTexto = re.sub(r'[";\*#]', '', var_strTexto)
        
        # Separa por vírgula e adiciona ao set
        var_listSeparadas = [var_strNome.strip() for var_strNome in var_strTexto.split(',') if var_strNome.strip()]
        
        return var_listSeparadas
    
    @classmethod
    def _inserir_novas_linguagens(cls, arg_listNovasLinguagens: List[str], arg_setLinguagensNormalizadas: set) -> list:
        """
        Processa e normaliza linguagens de steam_raw, inserindo novas na tabela steam_linguagens.
        
        Parâmetros:
        - arg_listNovasLinguagens (List[str]): Lista de linguagens novas a serem inseridas.
        - arg_setLinguagensNormalizadas (set): Set de linguagens normalizadas.

        Retorna:
        - List[str]: Conjunto de linguagens normalizadas
        """
        try:
            logger.info("Inserindo novas linguagens no banco...")
            var_setLinguagensNormalizadas = set(arg_setLinguagensNormalizadas)

            # Busca o MAX(id_linguagem) atual
            var_strSQLMax = "SELECT COALESCE(MAX(id_linguagem), 0) FROM public.steam_linguagens"
            var_connConnection = PostgreSQL.conectar()
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLMax)
                var_intMaxId = cursor.fetchone()[0]
            
            # Prepara dados para inserção
            var_listValores = [
                (var_intMaxId + var_intIdx + 1, var_strNome)
                for var_intIdx, var_strNome in enumerate(sorted(arg_listNovasLinguagens))
            ]
            
            # Insere usando execute_values para performance
            from psycopg2.extras import execute_values
            var_strSQLInsert = """
                INSERT INTO public.steam_linguagens (id_linguagem, nome_linguagem)
                VALUES %s
                ON CONFLICT (id_linguagem) DO NOTHING
            """
            
            with var_connConnection.cursor() as cursor:
                execute_values(cursor, var_strSQLInsert, var_listValores)
                var_connConnection.commit()
            
            logger.info(f"{len(arg_listNovasLinguagens)} linguagens inseridas com sucesso")
            
            # Log das novas linguagens
            logger.info("Novas linguagens adicionadas:")
            for _, var_strNome in var_listValores[:20]:  # Mostra apenas as primeiras 20
                logger.info(f"  • {var_strNome}")
            if len(var_listValores) > 20:
                logger.info(f"  ... e mais {len(var_listValores) - 20} linguagens")
            
            var_setLinguagensNormalizadas.update(arg_listNovasLinguagens)

            return list(var_setLinguagensNormalizadas)
        
        except Exception as e:
            if var_connConnection:
                var_connConnection.rollback()
            logger.error(f"Erro ao inserir novas linguagens: {e}")
            raise Exception(f"Erro ao inserir novas linguagens: {e}")
        finally:
            if var_connConnection:
                PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def processar_linguagens_completo(cls, arg_strLinguagens: str) -> List[str]:
        """
        Processa e normaliza linguagens de steam_raw, inserindo novas na tabela steam_linguagens.
        
        Parâmetros:
        - arg_strLinguagens (str): String bruta de linguagens do campo 'supported_languages' do steam_raw.

        Retorna:
        - List[str]: Conjunto de linguagens normalizadas
        """
        try:
            var_listSeparadas = cls.normalizar_texto(arg_strLinguagens)
            var_setLinguagensNormalizadas = set(var_listSeparadas)
            
            # Dicionário de tradução e normalização
            var_dictTraducao = cls._obter_dicionario_traducao_linguagens()
            
            # Criar novo set para linguagens normalizadas
            var_setLinguagensNormalizadasFinal = set()
            
            for var_strIdioma in var_setLinguagensNormalizadas:
                var_strNomeNormalizado = cls._normalizar_linguagem(var_strIdioma, var_dictTraducao)
                if var_strNomeNormalizado:
                    var_setLinguagensNormalizadasFinal.add(var_strNomeNormalizado)
            
            # Atualizar com linguagens normalizadas
            var_setLinguagensNormalizadas = var_setLinguagensNormalizadasFinal
            
            # Identifica linguagens que ainda não existem no BD
            var_dictLinguagensExistentes = PostgreSQLSteam.buscar_dados_linguagens()
            
            var_listNovasLinguagens = [
                var_strNome for var_strNome in var_setLinguagensNormalizadas
                if var_strNome not in var_dictLinguagensExistentes
            ]
            
            # Insere novas linguagens no banco
            if var_listNovasLinguagens:
                var_listLinguagensNormalizadas = cls._inserir_novas_linguagens(var_listNovasLinguagens, var_setLinguagensNormalizadas)
            else:
                var_listLinguagensNormalizadas = list(var_setLinguagensNormalizadas)
                
            return var_listLinguagensNormalizadas
            
        except Exception as e:
            logger.error(f"Erro no processamento de linguagens: {e}")
            raise
        
    @staticmethod
    def _normalizar_linguagem(arg_strNome: str, arg_dictTraducao: Dict[str, str]) -> str:
        """
        Normaliza nome de linguagem usando dicionário de tradução.
        
        Parâmetros:
        - arg_strNome: Nome da linguagem bruto
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
    def _obter_dicionario_traducao_linguagens() -> Dict[tuple, str]:
        """
        Retorna dicionário de tradução para normalização de linguagens.
        Baseado no SQL original com CASE WHEN ... ILIKE ANY(ARRAY[...])
        
        Retorna:
        - Dict[tuple, str]: {(padrão1, padrão2, ...): nome_normalizado}
        """
        return {
            # Casos Específicos/Compostos (prioridade)
            ('américa latina', 'latin america'): 'Espanhol (América Latina)',
            ('português (brasil)', 'portuguese - brazil', 'portuguese-brazil'): 'Português (Brasil)',
            ('português (portugal)', 'portuguese - portugal'): 'Português (Portugal)',
            ('chinês simplificado', 'simplified chinese', 'chinois simplifié', 'chin??s simplificado'): 'Chinês (Simplificado)',
            ('chinês tradicional', 'traditional chinese', 'chinois traditionnel', 'chin??s tradicional'): 'Chinês (Tradicional)',
            ('panjábi', 'punjabi', 'panj??bi'): 'Panjábi',
            ('ânglico', 'scots', '??nglico'): 'Ânglico (Escócia)',
            ('quíchua', 'quechua', 'qu??chua'): 'Quíchua',
            ('quiché', 'quich??'): 'Quiché',
            
            # Tradução Geral
            ('inglês', 'english', 'anglais', 'ingl??s'): 'Inglês',
            ('espanhol', 'spanish', 'espagnol'): 'Espanhol (Espanha)',
            ('português', 'portuguese', 'portugu??s'): 'Português',
            ('francês', 'french', 'français', 'franc??s'): 'Francês',
            ('alemão', 'german', 'allemand', 'alem??o'): 'Alemão',
            ('italiano', 'italian', 'italien'): 'Italiano',
            ('japonês', 'japanese', 'japonais', 'japon??s'): 'Japonês',
            ('coreano', 'korean', 'coréen'): 'Coreano',
            ('russo', 'russian'): 'Russo',
            ('tcheco', 'czech'): 'Tcheco',
            ('polonês', 'polish', 'polon??s'): 'Polonês',
            ('turco', 'turkish'): 'Turco',
            ('árabe', 'arabic', '??rabe'): 'Árabe',
            ('tailandês', 'thai', 'tailand??s'): 'Tailandês',
            ('holandês', 'dutch', 'holand??s'): 'Holandês',
            ('sueco', 'swedish'): 'Sueco',
            ('dinamarquês', 'danish', 'dinamarqu??s'): 'Dinamarquês',
            ('finlandês', 'finnish', 'finland??s'): 'Finlandês',
            ('norueguês', 'norwegian', 'noruegu??s'): 'Norueguês',
            ('húngaro', 'hungarian', 'h??ngaro'): 'Húngaro',
            ('ucraniano', 'ukrainian'): 'Ucraniano',
            ('vietnamita', 'vietnamese'): 'Vietnamita',
            ('romeno', 'romanian'): 'Romeno',
            ('grego', 'greek'): 'Grego',
            ('búlgaro', 'bulgarian', 'b??lgaro'): 'Búlgaro',
            ('africâner', 'afrikaans', 'afric??ner'): 'Africâner',
            ('albanês', 'albanian', 'alban??s'): 'Albanês',
            ('amárico', 'amharic', 'am??rico'): 'Amárico',
            ('armênio', 'armenian', 'arm??nio'): 'Armênio',
            ('assamês', 'assamese', 'assam??s'): 'Assamês',
            ('azerbaidjano', 'azerbaijani', 'azeri'): 'Azerbaidjano',
            ('basco', 'basque'): 'Basco',
            ('bielorrusso', 'belarusian'): 'Bielorrusso',
            ('bengali', 'bangla'): 'Bengali',
            ('bósnio', 'bosnian', 'b??snio'): 'Bósnio',
            ('catalão', 'catalan', 'catal??o'): 'Catalão',
            ('cazaque', 'kazakh'): 'Cazaque',
            ('cingalês', 'sinhala', 'cingal??s'): 'Cingalês',
            ('croata', 'croatian'): 'Croata',
            ('eslovaco', 'slovak', 'lang_slovakian'): 'Eslovaco',
            ('esloveno', 'slovenian'): 'Esloveno',
            ('estoniano', 'estonian'): 'Estoniano',
            ('filipino',): 'Filipino',
            ('galego', 'galician'): 'Galego',
            ('galês', 'welsh', 'gal??s'): 'Galês',
            ('georgiano', 'georgian'): 'Georgiano',
            ('guzerate', 'gujarati'): 'Guzerate',
            ('hauçá', 'hausa', 'hau????'): 'Hauçá',
            ('hebraico', 'hebrew'): 'Hebraico',
            ('hindi',): 'Hindi',
            ('indonésio', 'indonesian', 'indon??sio'): 'Indonésio',
            ('irlandês', 'irish', 'irland??s'): 'Irlandês',
            ('islandês', 'icelandic', 'island??s'): 'Islandês',
            ('canarês', 'kannada', 'canar??s'): 'Canarês',
            ('khmer',): 'Khmer',
            ('quiniaruanda', 'kinyarwanda'): 'Quiniaruanda',
            ('quirguiz', 'kyrgyz'): 'Quirguiz',
            ('letão', 'latvian', 'let??o'): 'Letão',
            ('lituano', 'lithuanian'): 'Lituano',
            ('luxemburguês', 'luxembourgish', 'luxemburgu??s'): 'Luxemburguês',
            ('macedônio', 'macedonian', 'maced??nio'): 'Macedônio',
            ('malaio', 'malay'): 'Malaio',
            ('malaiala', 'malayalam'): 'Malaiala',
            ('maltês', 'maltese', 'malt??s'): 'Maltês',
            ('maori',): 'Maori',
            ('marata', 'marathi'): 'Marata',
            ('mongol', 'mongolian'): 'Mongol',
            ('nepalês', 'nepali', 'nepal??s'): 'Nepalês',
            ('oriá', 'odia', 'ori??'): 'Oriá',
            ('persa', 'persian'): 'Persa',
            ('sérvio', 'serbian', 's??rvio'): 'Sérvio',
            ('sesoto', 'sotho'): 'Sesoto',
            ('sindi', 'sindhi'): 'Sindi',
            ('sorâni', 'sorani', 'sor??ni'): 'Sorâni',
            ('suaíli', 'swahili', 'sua??li'): 'Suaíli',
            ('tajique', 'tajik'): 'Tajique',
            ('tâmil', 'tamil', 't??mil'): 'Tâmil',
            ('tártaro', 'tatar', 't??rtaro'): 'Tártaro',
            ('télugo', 'telugu', 't??lugo'): 'Télugo',
            ('tigrínia', 'tigrinya', 'tigr??nia'): 'Tigrínia',
            ('tsuana', 'tswana'): 'Tsuana',
            ('turcomeno', 'turkmen'): 'Turcomeno',
            ('uigur', 'uyghur'): 'Uigur',
            ('uzbeque', 'uzbek'): 'Uzbeque',
            ('uolofe', 'wolof'): 'Uolofe',
            ('urdu',): 'Urdu',
            ('xossa', 'xhosa'): 'Xossa',
            ('iorubá', 'yoruba', 'iorub??'): 'Iorubá',
            ('zulu',): 'Zulu',
            ('concani', 'konkani'): 'Concani',
            ('cherokee',): 'Cherokee',
            ('valenciano', 'valencian'): 'Valenciano',
            ("k'iche'",): "K'iche'",
            ('dari',): 'Dari',
            ('igbo',): 'Igbo',
        }
