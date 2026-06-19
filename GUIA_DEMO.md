# Guía de ejecución y grabación del demo — EstrategIA Legal

Documento único para **poner a correr el programa de cero** y **grabar el video** del
demo. Pensado para cualquier integrante del equipo, técnico o no.

> ⚠️ **Antes de grabar:** el sistema solo produce un memorando útil si el `corpus/`
> tiene contenido jurídico real (lo cargan los abogados) y existe un PDF de demanda
> en `samples/`. Sin eso, la app **arranca pero avisa "corpus vacío"** y no genera
> resultados de demostración. Ver **Prerequisito 2**.

---

## 0. Resumen en 6 pasos

```
1. Python 3.12  →  2. Corpus cargado (abogados)  →  3. pip install
4. ANTHROPIC_API_KEY en .env  →  5. python -m src.rag.ingest  →  6. streamlit run app.py
```

---

## 1. Prerequisito técnico — Python 3.12

Usa **Python 3.12** (sirve 3.11–3.13). **No uses 3.14**: aún no hay paquetes
(`torch` / `sentence-transformers`) para los embeddings locales y la recuperación no
funcionará.

**macOS (Homebrew):**
```bash
brew install python@3.12
python3.12 --version          # debe decir 3.12.x
```

**Con pyenv (alternativa multiplataforma):**
```bash
pyenv install 3.12
pyenv local 3.12
```

---

## 2. Prerequisito jurídico — contenido del `corpus/` (lo cargan los abogados)

El programa **cita únicamente lo que esté en `corpus/`** (regla anti-alucinación). Para
un demo de tránsito hace falta, como mínimo:

| Carpeta / archivo | Qué va | Mínimo para el demo |
|---|---|---|
| `corpus/normas/` | Artículos de norma (un `.md` por norma) | C. Civil arts. 2341, 2347, 2354, 2356; Ley 769/2002 |
| `corpus/jurisprudencia/` | Sentencias (`.md` o `.json`) | 1–2 sentencias CSJ sobre nexo causal / quantum |
| `corpus/tablas/` | Tabla SOAT (Decreto 056/2015) | 1 archivo con los valores |
| `corpus/regimen_table.yaml` | hecho → régimen → normas → matiz | entrada `transito` diligenciada |
| `corpus/rubrica_solidez.md` | Criterios para ordenar argumentos | revisado/validado |
| `samples/` | PDF de la demanda a analizar | 1 demanda de tránsito (puede ser ficticia) |

**Formato de una norma** (`corpus/normas/cc_2356.md`):
```markdown
---
id: cc_2356
fuente: Código Civil de Colombia
seccion: Artículo 2356
url: https://www.suin-juriscol.gov.co/...
---
Por regla general todo daño que pueda imputarse a malicia o negligencia
de otra persona, debe ser reparado por ésta... [TEXTO LITERAL VERIFICADO]
```

**Entrada en `regimen_table.yaml`:**
```yaml
  transito:
    regimen: objetiva          # o subjetiva_culpa_presunta (criterio de los abogados)
    normas: [cc_2356]          # cada id DEBE existir como archivo en corpus/
    matiz_doctrinal: "Describir la discusión doctrinal/jurisprudencial..."
    respaldo: [csj_sc4407_2023]
```

> **Reglas que no se pueden romper:** `id` único y estable (estilo `cc_2356`); texto
> **literal** (no paráfrasis); cada `id` citado en `regimen_table.yaml` debe existir en
> `corpus/`, o el validador lo marca como cita huérfana (ERROR).

---

## 3. Prerequisito de API — clave de Claude

El razonamiento usa la API de Claude. Necesitas una `ANTHROPIC_API_KEY` (la provista en
el evento). Se configura en el paso 4.4.

---

## 4. Instalación desde cero

```bash
# 4.1 Clonar el repositorio
git clone https://github.com/brynzd/estrategia-legal-ai.git
cd estrategia-legal-ai

# 4.2 Entorno virtual con Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 4.3 Dependencias
pip install -r requirements.txt    # la primera vez baja torch (~varios cientos de MB)

# 4.4 Variables de entorno
cp .env.example .env               # editar .env y poner ANTHROPIC_API_KEY=sk-ant-...
```

---

## 5. Construir el índice del corpus

Tras cargar el `corpus/` (Prerequisito 2), genera el índice vectorial:

```bash
python -m src.rag.ingest
```

> La **primera vez** descarga el modelo de embeddings `intfloat/multilingual-e5-large`
> (~2.2 GB). Es de una sola vez. También puedes hacerlo desde la app con el botón
> **"🔄 Reconstruir índice del corpus"** de la barra lateral.
>
> Reconstruye el índice **cada vez que cambie el `corpus/`**.

---

## 6. Lanzar la aplicación

```bash
streamlit run app.py
```

Abre el navegador en **http://localhost:8501**.

---

## 7. Verificación antes de grabar (checklist)

En la **barra lateral** de la app, confirma:

- [ ] **LLM:** `anthropic`
- [ ] **API key:** ✅ presente
- [ ] **Fuentes en el corpus:** un número > 0 (si dice 0, falta el Prerequisito 2)
- [ ] **Índice RAG:** ✅ construido

Opcional, en la terminal: `pytest` debe dar **todos los tests en verde**.

---

## 8. Guion sugerido del video (5–7 min)

1. **Problema (30 s).** "Un abogado recibe una demanda de responsabilidad civil
   extracontractual y necesita una estrategia defensiva **trazable**, no un resumen de
   una caja negra."
2. **La app (20 s).** Muestra la barra lateral: corpus cargado, índice e LLM. Recalca:
   *"corpus cerrado y verificado por abogados"*.
3. **Subir la demanda (20 s).** Sube el PDF de `samples/` y pulsa **Analizar demanda**.
4. **Memorando (90 s).** Recorre las secciones: **argumentos ordenados por solidez**
   (ALTA → BAJA), cada afirmación con su cita `[FUENTE: <id>]`.
5. **Panel de trazabilidad (120 s) — el punto fuerte.** Abre los pasos en orden:
   Encuadre → Recuperación RAG → Régimen → Nexo / Exoneración / Perjuicio / Terceros →
   Memorando. *"No resume el PDF: razona paso a paso y deja registro de cada decisión."*
6. **Validación de citas (60 s) — el diferenciador.** Muestra el banner verde y los
   **enlaces a la fuente oficial** de cada cita. *"Cero alucinación: cada cita existe
   en el corpus y es verificable por un humano."*
7. **Cierre (30 s).** Diferenciador frente a un LLM genérico: **trazabilidad + derecho
   colombiano verificado**. Recuerda el *disclaimer*: documento de apoyo, no sustituye
   al abogado.

---

## 9. Solución de problemas

| Mensaje / síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: torch` / `sentence_transformers` | venv en Python 3.14 | Recrea el venv con **Python 3.12** (paso 1) |
| Barra lateral: **API key ❌** | falta la clave | Pon `ANTHROPIC_API_KEY` en `.env` |
| Barra lateral: **Índice ❌** | no se ha indexado | `python -m src.rag.ingest` o botón de la sidebar |
| **Fuentes: 0** / aviso "corpus vacío" | `corpus/` sin contenido real | Los abogados deben cargar el Prerequisito 2 |
| Memorando con **citas huérfanas** (rojo) | se citó un `id` que no está en `corpus/` | Revisa que los `id` de `regimen_table.yaml` existan como archivo |
| La app no abre | puerto ocupado | `streamlit run app.py --server.port 8502` |

---

## 10. (Bonus) Deploy en Streamlit Community Cloud — enlace que vive ≥30 días

1. Repo público en GitHub (ya existe) con `corpus/` **incluido** (no ignorado).
2. En share.streamlit.io: conecta el repo, archivo principal `app.py`.
3. En *Settings → Secrets* añade `ANTHROPIC_API_KEY`.
4. Tras desplegar, usa el botón **"Reconstruir índice del corpus"** (en el contenedor no
   existe `data/`).

> ⚠️ El modelo `e5-large` (~2.2 GB) puede exceder la RAM/disco del *free tier*. Si falla,
> baja a un modelo más liviano poniendo en *Secrets*
> `EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` y
> reconstruye el índice.
