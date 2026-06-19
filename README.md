# EstrategIA Legal

> Asistente de análisis defensivo en Responsabilidad Civil Extracontractual
> (Colombia). Recibe una demanda en PDF y produce un memorando de estrategia
> defensiva trazable**, mostrando su razonamiento jurídico paso a paso.

![UI](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![LLM](https://img.shields.io/badge/LLM-Claude%20%7C%20Groq-8A2BE2)


## Arquitectura

```
 PDF demanda
     │
     ▼
 1. Extracción ............. src/extraction.py        (PyMuPDF)
 2. Encuadre del caso ...... src/reasoning/case_framing.py   -> JSON de hechos
 3. Clasif. de régimen ..... src/reasoning/regime.py         (corpus/regimen_table.yaml)
 4. Recuperación RAG ....... src/rag/retriever.py            (corpus + embeddings locales)
 5. Razonamiento ........... src/reasoning/{causation,exoneration,damages,third_parties}.py
 6. Memorando .............. src/memo/builder.py             (orden por solidez)
 7. Validación de citas .... src/memo/validator.py            (anti-alucinación)
     │
     ▼
 Memorando + Panel de trazabilidad   (app.py — Streamlit)
```


## Estructura del proyecto

```
estrategia-legal-ai/
├── app.py                  # UI Streamlit (entrypoint)
├── requirements.txt
├── pyproject.toml          # metadatos + config de pytest
├── .env.example            # plantilla de variables de entorno
├── corpus/                 # fuente de verdad jurídica (la autoran los abogados)
│   ├── normas/             #   artículos de código, leyes, decretos
│   ├── jurisprudencia/     #   sentencias
│   ├── tablas/             #   tabla SOAT (Decreto 056/2015), etc.
│   ├── regimen_table.yaml  #   hecho -> régimen -> normas -> matiz  (PENDIENTE validación)
│   └── rubrica_solidez.md  #   criterios para ordenar argumentos    (PENDIENTE validación)
├── samples/                # demandas de muestra (PDF)
├── src/
│   ├── config.py           # paths, modelos, parámetros
│   ├── trace.py            # trazabilidad por paso (Restricción #3)
│   ├── extraction.py       # Paso 1 — PDF -> texto (PyMuPDF)
│   ├── pipeline.py         # orquestación secuencial
│   ├── llm/
│   │   └── client.py       # cliente LLM parametrizable (Claude/Groq)
│   ├── rag/
│   │   ├── corpus_loader.py  # lee corpus/ (md + JSON)
│   │   ├── embeddings.py     # capa de embeddings inyectable
│   │   ├── vector_store.py   # índice numpy (coseno, persistente en disco)
│   │   ├── ingest.py         # fragmenta + embebe + persiste
│   │   └── retriever.py      # recuperación top-k con trazabilidad de id
│   ├── reasoning/
│   │   ├── _common.py        # contrato de citas, formateo, parseo JSON
│   │   ├── case_framing.py   # Paso 2 — hechos estructurados
│   │   ├── regime.py         # Paso 3 — clasificación de régimen
│   │   ├── causation.py      # Paso 5 — nexo causal
│   │   ├── exoneration.py    # Paso 5 — exoneración + concurrencia de culpas
│   │   ├── damages.py        # Paso 5 — perjuicio + contraste SOAT
│   │   ├── third_parties.py  # Paso 5 — vinculación de terceros
│   │   └── analyze.py        # Paso 4 + orquestación — recupera por issue y encadena los pasos
│   └── memo/
│       ├── builder.py        # Paso 6 — ensamblado del memorando
│       └── validator.py      # Paso 7 — validación de citas (anti-alucinación) 
└── tests/                  # 46 tests (sin red ni API)
```

##  Stack

| Capa            | Tecnología                                              |
|-----------------|---------------------------------------------------------|
| PDF             | PyMuPDF (`fitz`) · `pdfplumber` para tablas difíciles   |
| Embeddings      | `sentence-transformers` local (e5-large / bge-m3) — pendiente descarga |
| Vector store    | numpy local (coseno, persistente) — `chroma-hnswlib` no soporta Python 3.14 |
| LLM razonamiento| Claude API (por defecto) · Groq (alternativa open)      |
| Orquestación    | Funciones Python secuenciales + logging por paso        |
| UI              | Streamlit                                               |

Local-first, costo ≈ 0: los embeddings y el vector store corren en local; solo el
LLM de razonamiento usa API.

## Run

> **Requisito:** Python **3.11+**.

```bash
# 1. Entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Claves de API (se leen de .env; .env está en .gitignore)
cp .env.example .env               # editar y poner ANTHROPIC_API_KEY

# 4. Índice del corpus (primera vez; o usa el botón de la barra lateral de la app)
python -m src.rag.ingest

# 5. UI
streamlit run app.py
```

### Tests

```bash
pytest
```

## Límites

- Depende del corpus que carguen los abogados; con el corpus vacío la app arranca,
  avisa y no produce resultados útiles.
- Embeddings reales (`sentence-transformers`) pendientes de descarga; el vector
  store usa numpy porque `chroma-hnswlib` no tiene wheel para Python 3.14.
- Es un documento de **apoyo**, no asesoría legal: el abogado valida cada cita y
  conclusión contra la fuente oficial.

---

<sub>Proyecto académico / Hackathon. Universidad ICESI.</sub>
