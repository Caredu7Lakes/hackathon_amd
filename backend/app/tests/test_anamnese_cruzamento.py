"""Teste determinístico do cruzamento anamnese × exame (LOINC).

Sem LLM, sem I/O de rede: exercita classificação por corte e o mapa de
concordância/discrepância. Caso-âncora: paciente nega diabetes, glicemia
laboratorial em 118 mg/dL -> discrepância de pré-diabetes.
"""

from app.schemas.anamnese import Anamnese, DiabetesStatus
from app.services.anamnese_service import (
    AchadoClinico,
    classificar_glicemia,
    classificar_pa,
    cruzar_anamnese_exames,
    LOINC_GLICEMIA_JEJUM,
    LOINC_PA_SISTOLICA,
    LOINC_PA_DIASTOLICA,
)


def _anamnese_base(**over) -> Anamnese:
    dados = dict(
        paciente_id="1", idade=52, sexo="masculino", ocupacao="motorista",
        motivo="check-up", diabetes_previo=DiabetesStatus.nao,
        hipertensao_previa=False,
    )
    dados.update(over)
    return Anamnese(**dados)


def test_classificar_glicemia_cortes_ada():
    assert classificar_glicemia(85).rotulo == "normal"
    assert classificar_glicemia(118).rotulo == "pre_diabetes"
    assert classificar_glicemia(140).rotulo == "diabetes"


def test_classificar_pa_hipertensao():
    assert classificar_pa(120, 80).rotulo == "normal"
    assert classificar_pa(148, 92).rotulo == "hipertensao"
    assert classificar_pa(130, 92).rotulo == "hipertensao"  # só diastólica alta


def test_discrepancia_glicemia_nega_diabetes():
    anamnese = _anamnese_base(diabetes_previo=DiabetesStatus.nao)
    achados = [AchadoClinico(loinc=LOINC_GLICEMIA_JEJUM, valor=118)]
    r = cruzar_anamnese_exames(anamnese, achados)
    assert len(r) == 1
    assert r[0].tipo == "discrepancia"
    assert r[0].dominio == "glicemia"
    assert "pre_diabetes" in r[0].exame


def test_concordancia_glicemia_relata_diabetes():
    anamnese = _anamnese_base(diabetes_previo=DiabetesStatus.diabetes)
    achados = [AchadoClinico(loinc=LOINC_GLICEMIA_JEJUM, valor=140)]
    r = cruzar_anamnese_exames(anamnese, achados)
    assert r[0].tipo == "concordancia"


def test_discrepancia_pa_nega_hipertensao():
    anamnese = _anamnese_base(hipertensao_previa=False)
    achados = [
        AchadoClinico(loinc=LOINC_PA_SISTOLICA, valor=148),
        AchadoClinico(loinc=LOINC_PA_DIASTOLICA, valor=92),
    ]
    r = cruzar_anamnese_exames(anamnese, achados)
    assert any(c.dominio == "pressao_arterial" and c.tipo == "discrepancia" for c in r)


def test_glicemia_normal_sem_flag():
    anamnese = _anamnese_base(diabetes_previo=DiabetesStatus.nao)
    achados = [AchadoClinico(loinc=LOINC_GLICEMIA_JEJUM, valor=85)]
    r = cruzar_anamnese_exames(anamnese, achados)
    assert r == []


def test_loinc_desconhecido_ignorado():
    anamnese = _anamnese_base()
    achados = [AchadoClinico(loinc="9999-9", valor=999)]  # LOINC sem regra
    r = cruzar_anamnese_exames(anamnese, achados)
    assert r == []