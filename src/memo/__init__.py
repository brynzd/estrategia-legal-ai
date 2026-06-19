"""Ensamblado del memorando y validación de citas (Pasos 6 y 7).

Submódulos:
    builder     Paso 6 — ensambla los pasos de razonamiento en un memorando
                estructurado, ordenando los argumentos por solidez según
                `corpus/rubrica_solidez.md`, con disclaimer de documento de apoyo.
    validator   Paso 7 — parsea las citas `[FUENTE: <id>]` y verifica que cada
                `id` exista en el corpus (Restricción dura #2). Ya implementado.
"""
