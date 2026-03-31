"""Roteador de banco de dados por domínio (app Django).

Cada app do ETL possui seu banco destino separado.
O roteador direciona leituras, escritas e migrações para o banco correto.

Mapa de roteamento:
    institucional → institucional_db  (INSTITUCIONAL_DB)
    professores   → professores_db    (PROFESSORES_DB)
    alunos        → alunos_db         (ALUNOS_DB)
    pedagogico    → pedagogico_db     (PEDAGOGICO_DB)
    programas     → programas_db      (PROGRAMAS_DB)

Apps sem mapeamento explícito (controle_auditoria, escolas,
eol_connection) continuam usando o banco `default`.

Nota: dominios_auxiliar foi removido — suas tabelas de referência
são embarcadas em cada domínio que as necessita.
"""

_APP_PARA_BANCO: dict[str, str] = {
    "institucional": "institucional_db",
    "professores": "professores_db",
    "alunos": "alunos_db",
    "pedagogico": "pedagogico_db",
    "programas": "programas_db",
}


class DominioRouter:
    """Roteia modelos dos domínios de negócio para seus bancos dedicados."""

    def db_for_read(self, model: type, **_hints: object) -> str | None:
        """Direciona leitura para o banco do domínio."""
        return _APP_PARA_BANCO.get(model._meta.app_label)  # type: ignore[attr-defined]

    def db_for_write(self, model: type, **_hints: object) -> str | None:
        """Direciona escrita para o banco do domínio."""
        return _APP_PARA_BANCO.get(model._meta.app_label)  # type: ignore[attr-defined]

    def allow_relation(  # noqa: E501
        self, obj1: object, obj2: object, **_hints: object
    ) -> bool | None:
        """Permite relações apenas dentro do mesmo banco."""
        db1 = _APP_PARA_BANCO.get(obj1._meta.app_label, "default")  # type: ignore[attr-defined]
        db2 = _APP_PARA_BANCO.get(obj2._meta.app_label, "default")  # type: ignore[attr-defined]
        if db1 == db2:
            return True
        return None

    def allow_migrate(
        self, db: str, app_label: str, _model_name: str | None = None, **_hints: object
    ) -> bool | None:
        """Garante que cada app migre apenas no banco correto."""
        banco_destino = _APP_PARA_BANCO.get(app_label)
        if banco_destino:
            return db == banco_destino
        if db in _APP_PARA_BANCO.values():
            # Impede que apps do default migrem nos bancos de domínio
            return False
        return None
