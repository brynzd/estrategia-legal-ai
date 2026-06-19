"""Cliente LLM parametrizable (Claude por defecto / Groq alternativo).

Expone una interfaz mínima `complete(system, prompt)` para que los pasos de
razonamiento no conozcan el proveedor. La selección se hace por configuración
(`config.LLM_PROVIDER`); las claves se leen del entorno (`.env`).

Para poder probar los pasos sin gastar API ni necesitar clave, los pasos reciben
una `LLMFn` inyectable (ver `src/reasoning/_common.py`); en producción usan
`get_default_llm()`, que envuelve a `complete()`.
"""

from __future__ import annotations

from typing import Callable

from .. import config

# Una LLMFn recibe (system, prompt) y devuelve el texto de la respuesta del modelo.
LLMFn = Callable[[str, str], str]

DEFAULT_MAX_TOKENS = 4096


def complete(
    system: str,
    prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Genera una respuesta del LLM configurado.

    Args:
        system: Instrucción de sistema (incluye el contrato de citas).
        prompt: Mensaje del usuario con los hechos y los fragmentos recuperados.
        temperature: Temperatura de muestreo; 0.0 por defecto para minimizar
            variabilidad en tareas jurídicas.
        max_tokens: Máximo de tokens de salida.
        provider: "anthropic" o "groq". Si es `None`, usa `config.LLM_PROVIDER`.
        model: Nombre del modelo. Si es `None`, usa el del proveedor en `config`.

    Returns:
        El texto de la respuesta del modelo.

    Raises:
        ValueError: Si el proveedor no es reconocido o falta la clave de API.
    """
    provider = (provider or config.LLM_PROVIDER).lower()
    if provider == "anthropic":
        return _complete_anthropic(system, prompt, temperature, max_tokens, model)
    if provider == "groq":
        return _complete_groq(system, prompt, temperature, max_tokens, model)
    raise ValueError(f"Proveedor de LLM no reconocido: {provider!r}")


def _complete_anthropic(
    system: str, prompt: str, temperature: float, max_tokens: int, model: str | None
) -> str:
    """Llama a la API de Claude (Anthropic)."""
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
    import anthropic  # import perezoso

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=model or config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def _complete_groq(
    system: str, prompt: str, temperature: float, max_tokens: int, model: str | None
) -> str:
    """Llama a la API de Groq (formato compatible OpenAI)."""
    if not config.GROQ_API_KEY:
        raise ValueError("Falta GROQ_API_KEY en el entorno (.env).")
    import groq  # import perezoso

    client = groq.Groq(api_key=config.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=model or config.GROQ_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def get_default_llm() -> LLMFn:
    """Devuelve una `LLMFn` que usa el proveedor configurado por defecto.

    Returns:
        Una función `(system, prompt) -> str` que llama a `complete()`.
    """
    return lambda system, prompt: complete(system, prompt)
