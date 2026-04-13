import io
import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Corretor de Redações")
app.mount("/static", StaticFiles(directory="static"), name="static")

MODEL = "gemini-2.0-flash"
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB


def get_model() -> genai.GenerativeModel:
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="Chave de API não configurada. Configure GOOGLE_API_KEY no servidor.",
        )
    genai.configure(api_key=key)
    return genai.GenerativeModel(MODEL)


def rubrica_label(rubrica: str) -> str:
    return {
        "enem": "ENEM (escala 0–200 por competência, total 1000 pts)",
        "jovem_senador": (
            "Jovem Senador 2026 (escala 0–2 por competência, total 10 pts — "
            "mínimo 20 linhas, máximo 30 linhas, sem título)"
        ),
        "outra": "Rubrica geral dissertativo-argumentativa",
    }.get(rubrica, "ENEM")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": MODEL}


@app.post("/api/analisar-imagem")
async def analisar_imagem(
    foto: UploadFile = File(...),
    tema: str = Form(...),
    rubrica: str = Form(default="enem"),
):
    """Etapa 1 + 3: análise visual da imagem e transcrição."""
    foto_bytes = await foto.read()
    if len(foto_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Imagem muito grande. Máximo: 20 MB.")

    try:
        img = Image.open(io.BytesIO(foto_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido ou corrompido.")

    prompt = f"""Você é um corretor especializado em redações com profundo conhecimento da rubrica oficial do INEP/MEC.

Esta é uma foto de uma redação manuscrita. Execute as Etapas 1 e 3 do fluxo de correção.

Tema da redação: {tema}
Rubrica aplicada: {rubrica_label(rubrica)}

## ETAPA 1 — Análise Visual da Imagem

Analise SOMENTE A IMAGEM — não transcreva ainda. Mapeie tudo que só pode ser avaliado visualmente.

Estrutura e formatação:
- Margens (esquerda, direita, superior, inferior)
- Alinhamento e recuo de parágrafo
- Contagem precisa de linhas escritas (crucial para verificar mínimo exigido pela rubrica)
- Rasuras: quantidade e localização
- Identificação proibida: nome, assinatura, desenhos fora do local correto
- Presença de título (para Jovem Senador: título é proibido)

Translineação (quebras de linha com hífen):
Para cada quebra com hífen: informe a separação silábica e se está correta ou incorreta.

Maiúsculas e minúsculas:
- Inícios de frase e parágrafo
- Nomes próprios
- Maiúsculas indevidas no meio de palavras

Marcadores de erro visíveis:
- Palavras com grafia suspeita (liste com localização aproximada)
- Pontuação ambígua
- Palavras de leitura incerta

## ETAPA 3 — Transcrição Guiada

Transcreva o texto preservando ABSOLUTAMENTE TODOS os erros do aluno exatamente como escritos.
Regras invioláveis:
- Nunca corrija ortografia, pontuação ou concordância
- Use [?] para palavras de leitura incerta
- Use [RASURA] para trechos ilegíveis
- Preserve a divisão em parágrafos do original

## FORMATO DE SAÍDA OBRIGATÓRIO

Responda EXATAMENTE neste formato, com as tags XML exatas:

<MAPA_VISUAL>
═══════════════════════════════════════════
MAPA DE EVIDÊNCIAS VISUAIS
═══════════════════════════════════════════

📐 ESTRUTURA FÍSICA
[observações]

✂️ TRANSLINEAÇÃO
[lista de cada quebra com avaliação]

🔤 MAIÚSCULAS E MINÚSCULAS
[observações]

⚠️ MARCADORES DE ERRO
[lista]

📌 PALAVRAS COM LEITURA INCERTA
[lista]
═══════════════════════════════════════════
</MAPA_VISUAL>

<TRANSCRICAO>
[texto do aluno transcrito, preservando todos os erros, com parágrafos separados por linha em branco]
</TRANSCRICAO>"""

    try:
        model = get_model()
        response = model.generate_content([prompt, img])
        return {"resultado": response.text}
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro na API do Gemini: {e}")


@app.post("/api/analisar-competencias")
async def analisar_competencias(
    mapa_visual: str = Form(...),
    transcricao: str = Form(...),
    tema: str = Form(...),
    rubrica: str = Form(default="enem"),
):
    """Etapa 4: análise pelas competências, usando a transcrição confirmada pela professora."""

    if rubrica == "enem":
        rubrica_prompt = """## RUBRICA ENEM (0–200 por competência · total 1000 pts)

Verifique primeiro as condições de NOTA ZERO:
- Texto em branco | menos de 7 linhas | fuga total ao tema
- Estrutura não dissertativa (narração, poema, lista)
- Cópia dos textos motivadores | identificação proibida

Verifique TANGENCIAMENTO: texto trata o assunto geral mas não o tema específico proposto
→ se sim: C II, C III e C V ficam limitadas a 40 pts.

COMPETÊNCIA I — Domínio da Modalidade Escrita Formal
Avalie: ortografia, acentuação, morfossintaxe, pontuação, maiúsculas/minúsculas e translineação (do mapa visual).
Níveis: 0(0) | 1(40) | 2(80) | 3(120) | 4(160) | 5(200)

COMPETÊNCIA II — Compreensão da Proposta e Desenvolvimento do Tema
Avalie: leitura do tema específico, tese, repertório sociocultural (produtivo vs. de bolso), estrutura dissertativo-argumentativa.
Repertório produtivo: citações com autoria, dados de fontes verificáveis, obras pertinentes.
Repertório de bolso: "estudos mostram", "é sabido que", provérbios sem fonte, experiência pessoal genérica.
Níveis: 0(0) | 1(40) | 2(80) | 3(120) | 4(160) | 5(200)

COMPETÊNCIA III — Organização e Progressão das Ideias
Avalie (teoria Koch): unidade temática, progressão lógica, articulação entre parágrafos, ausência de contradições, conclusão que decorre dos argumentos.
Níveis: 0(0) | 1(40) | 2(80) | 3(120) | 4(160) | 5(200)

COMPETÊNCIA IV — Mecanismos Linguísticos de Coesão
Avalie: conectivos e operadores (uso correto?), referenciação (pronomes, sinônimos, hiperônimos), variedade de recursos coesivos.
Níveis: 0(0) | 1(40) | 2(80) | 3(120) | 4(160) | 5(200)

COMPETÊNCIA V — Proposta de Intervenção
Verifique os 5 elementos: Ação | Agente específico | Meio/Modo | Efeito/Finalidade | Detalhamento.
Verifica respeito aos direitos humanos. Articulação com a argumentação desenvolvida.
Níveis: 0(0) | 1(40) | 2(80) | 3(120) | 4(160) | 5(200)

Tabela de pontuação:
C I: [ ] pts | C II: [ ] pts | C III: [ ] pts | C IV: [ ] pts | C V: [ ] pts | TOTAL: [ ]/1000 pts"""

    elif rubrica == "jovem_senador":
        rubrica_prompt = """## RUBRICA JOVEM SENADOR 2026 (0–2 por competência · total 10 pts)

Verifique primeiro as condições de DESCLASSIFICAÇÃO:
- Menos de 20 linhas → desclassificação
- Mais de 30 linhas → desclassificação
- Título presente → desclassificação
- Identificação no corpo do texto → desclassificação

Verifique TANGENCIAMENTO: o texto trata do assunto geral mas não responde ao tema específico.

C1 — Domínio da norma escrita: 0 = não demonstra | 1 = parcialmente | 2 = plenamente
C2 — Compreensão do tema e do gênero: 0 = fuga/fora do gênero | 1 = tangencia | 2 = compreende e desenvolve
C3 — Argumentação e conteúdo: 0 = sem argumentação | 1 = superficial | 2 = consistente com repertório
C4 — Organização textual e coesão: 0 = sem organização | 1 = parcial | 2 = bem organizado e coeso
C5 — Proposta de intervenção respeitando a cidadania: 0 = ausente/fere DH | 1 = vaga | 2 = clara, articulada, criativa, respeita DH

Tabela de pontuação:
C1: [ ] pts | C2: [ ] pts | C3: [ ] pts | C4: [ ] pts | C5: [ ] pts | TOTAL: [ ]/10 pts"""

    else:
        rubrica_prompt = """## ANÁLISE QUALITATIVA GERAL
Analise: domínio da norma culta, compreensão do tema, qualidade argumentativa, coesão e coerência, conclusão/proposta."""

    prompt = f"""Você é um corretor especializado em redações.

MAPA VISUAL CONFIRMADO PELA PROFESSORA:
{mapa_visual}

TRANSCRIÇÃO CONFIRMADA PELA PROFESSORA (erros preservados):
{transcricao}

Tema: {tema}

{rubrica_prompt}

## FORMATO DO RELATÓRIO FINAL

══════════════════════════════════════════════════════
CORREÇÃO COMPLETA
Tema: {tema}
══════════════════════════════════════════════════════

⚠️ CONDIÇÕES ESPECIAIS
[desclassificação / nota zero / tangenciamento / nenhuma — com justificativa]

──────────────────────────────────────────────────────
COMPETÊNCIA [número] — [nome]
Nível: [ ] | Pontuação: [ ] pts

Desvios/Observações:
• "[trecho exato do texto]" → [tipo de problema]

Justificativa: [explicação fundamentada]

[repetir para cada competência]
──────────────────────────────────────────────────────
PONTUAÇÃO FINAL
[tabela]

⚠️ Esta pontuação é estimativa. A decisão final é da professora.
──────────────────────────────────────────────────────
PRIORIDADES DE FEEDBACK PARA A ALUNA
1. [competência + sugestão concreta e específica]
2. [competência + sugestão concreta e específica]
3. [competência + sugestão concreta e específica]
══════════════════════════════════════════════════════

Cite trechos reais do texto para fundamentar cada avaliação."""

    try:
        model = get_model()
        response = model.generate_content(prompt)
        return {"resultado": response.text}
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro na API do Gemini: {e}")


@app.post("/api/gerar-feedback")
async def gerar_feedback(
    relatorio: str = Form(...),
    nome_aluno: str = Form(default=""),
):
    """Gera mensagem de feedback simplificada e encorajadora para a aluna."""
    nome_parte = f" para {nome_aluno}" if nome_aluno.strip() else ""

    prompt = f"""Com base no relatório técnico de correção abaixo, escreva uma mensagem de feedback{nome_parte}.

Diretrizes da mensagem:
- Linguagem acessível e calorosa, sem jargão técnico de avaliação
- Comece reconhecendo algo positivo que a aluna fez bem
- Apresente exatamente 3 pontos de melhoria, de forma clara e prática (o que fazer, não apenas o que está errado)
- Tom de professora que acredita no potencial da aluna
- Máximo de 180 palavras
- Termine com uma frase de incentivo para a próxima redação
- Não use asteriscos nem marcadores como "•" ou "-", escreva em parágrafos corridos

RELATÓRIO TÉCNICO:
{relatorio}

Escreva apenas a mensagem, sem título nem explicações adicionais."""

    try:
        model = get_model()
        response = model.generate_content(prompt)
        return {"feedback": response.text}
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro na API do Gemini: {e}")
