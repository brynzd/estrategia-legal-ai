"""EstrategIA Legal — paquete principal.

Pipeline transparente de apoyo a la decisión defensiva en Responsabilidad Civil
Extracontractual (Colombia). Cada submódulo corresponde a un paso del pipeline
descrito en CLAUDE.md y PLAN.md:

    extraction      Paso 1  — PDF de la demanda -> texto plano (PyMuPDF).
    rag/            Paso 4  — corpus cerrado, embeddings locales y recuperación.
    reasoning/      Pasos 2,3,5 — encuadre, régimen y razonamiento jurídico.
    memo/           Pasos 6,7 — ensamblado del memorando y validación de citas.
    llm/            Cliente LLM parametrizable (Claude por defecto / Groq).
    pipeline        Orquestación secuencial con trazas por paso.
    config          Configuración central (paths, modelos, parámetros).
    trace           Registro entrada/salida por paso para el panel de trazabilidad.

Restricciones duras (ver CLAUDE.md): cero alucinación de fuentes, validación de
citas obligatoria y trazabilidad de toda conclusión jurídica.
"""

__version__ = "0.1.0"
