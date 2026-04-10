from typing import Optional, Any
from datetime import date
from apps.alunos.dtos.model_in import (
    AlunoIn, MatriculaIn, MatriculaTurmaIn, 
    ResponsavelAlunoIn, TipoNecessidadeEspecialIn,
    NecessidadeEspecialAlunoIn
)


def _strip(val: Any) -> Optional[str]:
    """Remove espaços e caracteres nulos (\x00), aceita qualquer tipo."""
    if val is None:
        return None
    s_val = str(val).strip().replace("\x00", "")
    return s_val if s_val else None

class AlunoOut:
    @staticmethod
    def to_dict(dto: AlunoIn) -> dict:        
        return {
            "codigo_aluno": dto.codigo_aluno,
            "nome": _strip(dto.nome) or "NÃO INFORMADO",
            "nome_social": _strip(dto.nome_social),
            "data_nascimento": dto.data_nascimento,
            "sexo": dto.sexo or "U",
            "nacionalidade": _strip(dto.nacionalidade) or "0",
            "nis": _strip(dto.nis),
            "cpf": _strip(dto.cpf),
            "raca_cor": _strip(dto.raca_cor) or "NÃO INFORMADA"
        }

class TipoNecessidadeEspecialOut:
    @staticmethod
    def to_dict(dto: TipoNecessidadeEspecialIn) -> dict:
        return {
            "codigo_necessidade_especial": dto.codigo_necessidade_especial,
            "descricao": _strip(dto.descricao),
            "codigo_estado": dto.codigo_estado,
            "data_cancelamento": dto.dt_cancelamento,
            "ativo": dto.dt_cancelamento is None
        }

class ResponsavelAlunoOut:
    @staticmethod
    def to_dict(dto: ResponsavelAlunoIn) -> dict:
        return {
            "codigo_responsavel": dto.codigo_responsavel,
            "aluno_id": dto.codigo_aluno,
            "tipo_responsavel": dto.tipo_responsavel,
            "nome": _strip(dto.nome),
            "cpf": _strip(dto.cpf),
            "email": _strip(dto.email),
            "ddd_celular": _strip(dto.ddd_celular),
            "numero_celular": _strip(dto.numero_celular),
            "autoriza_sms": dto.autoriza_sms,
            "logradouro": _strip(dto.logradouro),
            "cep": dto.cep,
            "data_fim_vinculo": dto.data_fim_vinculo_aluno
        }

class NecessidadeEspecialAlunoOut:
    @staticmethod
    def to_dict(dto: NecessidadeEspecialAlunoIn) -> dict:
        return {
            "codigo_necessidade_especial_aluno": dto.codigo_necessidade_especial_aluno,
            "aluno_id": dto.codigo_aluno,
            "necessidade_especial_id": dto.codigo_necessidade_especial,
            "data_inicio": dto.dt_inicio,
            "data_fim": dto.dt_fim
        }

class MatriculaOut:
    @staticmethod
    def to_dict(dto: MatriculaIn) -> dict:
        return {
            "codigo_matricula": dto.codigo_matricula,
            "aluno_id": dto.codigo_aluno,
            "codigo_ue": _strip(dto.codigo_ue),
            "data_status": dto.data_status,
            "ano_letivo": dto.ano_letivo,
            "codigo_situacao_matricula": dto.codigo_situacao_matricula,
            "situacao_matricula": _strip(dto.situacao_matricula)
        }

class MatriculaTurmaOut:
    @staticmethod
    def to_dict(dto: MatriculaTurmaIn) -> dict:
        return {
            "matricula_id": dto.codigo_matricula,
            "codigo_turma": dto.codigo_turma,
            "numero_chamada": _strip(dto.numero_chamada),
            "data_situacao_aluno": dto.data_situacao
        }

