# Glossário de Modelos do Domínio Institucional

Estes modelos residem em `apps/institucional/models.py` e são persistidos no banco de dados `institucional_db` (PostgreSQL).

## 1. DRE (Diretoria Regional de Educação)
Diretorias Regionais de Educação da SME.
- **Tabela**: `dre`
- **PK**: `codigo_dre` (CharField 20 - ex: "108900")
- **Campos Principais**: `nome`, `sigla`, `tipo_unidade_adm`.

## 2. TipoEscola
Classificação das unidades educacionais.
- **Tabela**: `tipo_escola`
- **PK**: `codigo_tipo_escola` (Integer)
- **Campos Principais**: `sigla` (ex: EMEF, CEI), `descricao`.

## 3. SubPrefeitura
Municípios onde a unidade educacional está localizada.
- **Tabela**: `sub_prefeitura`
- **PK**: `codigo_sub_prefeitura` (Integer)
- **Campos Principais**: `sg_sub_prefeitura`, `nome`.

## 4. UnidadeEducacional
A entidade principal do domínio, representando a escola.
- **Tabela**: `unidade_educacional`
- **PK**: `codigo_ue` (CharField 20 - ex: "001089")
- **RP**: `codigo_ue_integracao` (UUID do SSO legado) — *Crucial para integração com sistemas legados (Core SSO).*
- **Relacionamentos**:
    - `dre_id`: Vinculação administrativa.
    - `tipo_escola_id`: Classificação da unidade.
    - `subprefeitura_id`: Localização municipal.
- **Indicadores**: Armazena capacidade de vagas (`vagas_matutino`, `vagas_total`) e contagem de funcionários da extração do EOL.

## 5. DREAbrangencia
Projeção das DREs que possuem oferta educacional válida para abrangência.
- **Tabela**: `dre_abrangencia`
- **PK**: `codigo_dre` (CharField 20)
- **Campos Principais**: `nome`, `abreviacao`, `ordem`.
