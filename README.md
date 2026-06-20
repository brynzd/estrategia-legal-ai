# EstrategIA Legal

> Asistente de análisis defensivo en Responsabilidad Civil Extracontractual
> (Colombia). Recibe una demanda en PDF y produce un memorando de estrategia
> defensiva trazable**, mostrando su razonamiento jurídico paso a paso.

![UI](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![LLM](https://img.shields.io/badge/LLM-Claude%20%7C%20Groq-8A2BE2)

## Base jurídica
La solución propuesta se fundamenta en un marco normativo y jurisprudencial que permite a la inteligencia artificial identificar, clasificar y analizar de manera diferenciada los diversos supuestos de responsabilidad civil extracontractual. En primer lugar, los artículos 2341, 2347, 2354 y 2356 del Código Civil colombiano constituyen la base para determinar el régimen de imputación aplicable en cada caso. El artículo 2341 desarrolla el principio general de responsabilidad por culpa, exigiendo la acreditación del daño, la conducta culposa y el nexo causal como elementos estructurales de la responsabilidad subjetiva. Por su parte, el artículo 2347 regula la responsabilidad por el hecho ajeno, permitiendo establecer eventos en los que una persona debe responder por los actos de quienes se encuentran bajo su cuidado o dependencia. A su vez, el artículo 2354 contempla la responsabilidad derivada de daños causados por animales fieros, mientras que el artículo 2356 se erige como una de las principales fuentes normativas para el análisis de actividades peligrosas, ámbito en el que la jurisprudencia ha reconocido regímenes de imputación más rigurosos debido al riesgo inherente de ciertas actividades. Complementariamente, la Ley 769 de 2002 (Código Nacional de Tránsito) proporciona los criterios normativos para la valoración de accidentes viales, permitiendo identificar infracciones a las normas de tránsito, determinar la participación de cada conductor en la producción del daño y evaluar escenarios de concurrencia de culpas, aspecto esencial para modular la responsabilidad y la indemnización correspondiente. En materia de responsabilidad médica, la Ley 23 de 1981 y la Ley 1751 de 2015 suministran los parámetros éticos, técnicos y constitucionales que orientan la prestación del servicio de salud, permitiendo a la herramienta verificar el cumplimiento de los deberes profesionales del personal médico y la eventual vulneración del derecho fundamental a la salud. Asimismo, la Ley 1480 de 2011, particularmente sus artículos 19 a 26, incorpora el régimen de responsabilidad objetiva por productos defectuosos, posibilitando que el sistema identifique aquellos eventos en los que la víctima no está obligada a demostrar la culpa del productor o proveedor, sino únicamente el defecto, el daño y la relación causal existente entre ambos. Este análisis normativo se fortalece con la doctrina desarrollada por la Corte Suprema de Justicia, Sala de Casación Civil, especialmente en la Sentencia SC4407-2023, la cual ofrece criterios relevantes para la valoración del nexo causal, la diferenciación entre culpa probada y culpa presunta, así como la determinación y cuantificación de los perjuicios indemnizables. Dicha jurisprudencia resulta particularmente útil para que la inteligencia artificial distinga los diferentes niveles y modalidades de imputación jurídica, identifique las cargas probatorias aplicables en cada escenario y proponga estrategias procesales acordes con el régimen de responsabilidad correspondiente. Finalmente, el Decreto 056 de 2015 aporta los parámetros técnicos para la liquidación de indemnizaciones derivadas de accidentes de tránsito cubiertos por el SOAT, permitiendo estimar de manera objetiva los perjuicios reconocibles conforme a la normativa vigente. En conjunto, este marco normativo dota a la herramienta de la capacidad de analizar integralmente los elementos de la responsabilidad civil extracontractual, evaluar causales de exoneración, identificar responsables directos e indirectos y generar respuestas jurídicas fundamentadas, coherentes y ajustadas al ordenamiento jurídico colombiano.

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
