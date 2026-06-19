"""Pasos de razonamiento jurídico (Pasos 2, 3 y 5 del pipeline).

Cada submódulo es una función aislada y testeable sobre la muestra de tránsito:

    case_framing    Paso 2 — PDF (texto) -> JSON de hechos estructurados.
    regime          Paso 3 — clasifica el régimen (citando regimen_table.yaml).
    causation       Paso 5 — nexo causal: identifica sus elementos.
    exoneration     Paso 5 — culpa exclusiva víctima / hecho de tercero / fuerza
                    mayor, incluida concurrencia de culpas.
    damages         Paso 5 — daño emergente y lucro cesante; contraste con SOAT;
                    pruebas de descargo concretas.
    third_parties   Paso 5 — llamamiento en garantía / denuncia del pleito.
    analyze         Paso 4 + orquestación — recupera del corpus por cada issue y
                    encadena los pasos anteriores dejando una traza por paso.

Contrato común (Restricciones duras #1 y #3): cada paso cita SOLO lo recuperado
con formato `[FUENTE: <id>]` y responde "No encontrado en el corpus" si la
información no está; toda conclusión se apoya en hechos + cita + razonamiento.
"""
