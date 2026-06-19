# Corpus jurídico (fuente de verdad)

> **El contenido jurídico lo definen y verifican los abogados.** El código no
> decide doctrina: solo mapea hechos a las reglas autoradas aquí y exige cita.
> Toda fuente debe tener texto **literal verificado** y `url` a la fuente oficial.

El sistema **solo** puede citar `id`s presentes en este corpus (Restricción dura
#1). Si algo no está aquí, la salida dice literalmente `"No encontrado en el corpus"`.

## Estructura

```
corpus/
├── normas/            # artículos de código, leyes, decretos
├── jurisprudencia/    # sentencias (CSJ, etc.)
├── tablas/            # tablas estructuradas (p. ej. SOAT — Decreto 056/2015)
├── regimen_table.yaml # hecho -> régimen -> normas -> matiz doctrinal (con id)
└── rubrica_solidez.md # criterios para ordenar argumentos de más a menos sólido
```

## Formato de una fuente

Un archivo por fuente, en **markdown con front-matter** o **JSON**. Campos:

| campo      | descripción                                              |
|------------|----------------------------------------------------------|
| `id`       | identificador único (p. ej. `cc_2356`, `csj_sc4407_2023`) |
| `fuente`   | nombre completo de la norma/sentencia                    |
| `seccion`  | artículo / sección (`articulo` también es válido)        |
| `texto`    | texto **literal verificado**                             |
| `url`      | enlace a la fuente oficial para verificación humana      |

Plantillas: `normas/_plantilla.md` y `jurisprudencia/_plantilla.md`.

## Convenciones

- El `id` es la clave de trazabilidad: aparece en cada cita `[FUENTE: <id>]` del
  memorando y lo verifica `src/memo/validator.py`. **Debe ser único y estable.**
- Los archivos cuyo nombre empieza con `_` (p. ej. `_plantilla.md`) se tratan
  como plantillas y se ignoran al cargar ids.
- Al añadir una fuente: duplica la plantilla, renómbrala con el `id` y rellena
  todos los campos con texto verificado y su `url`.
