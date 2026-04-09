"""
Sistema centralizado de traduções i18n.

Suporta chaves aninhadas nos arquivos JSON de tradução.
Idiomas: Inglês (en, padrão) e Português (pt).

Uso:
    from shared_utils.get_translations import t, get_translations

    # Acesso por chaves aninhadas
    t("pt", "sidebar", "title")        → "Calculadora ETo"
    t("en", "results", "new_query")    → "New Query"

    # Dicionário completo
    translations = get_translations("pt")
    translations["navbar"]["home"]     → "INÍCIO"

Arquivos:
    config/translations/en.json
    config/translations/pt.json
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Cache em memória para traduções já carregadas
_translations_cache: Dict[str, Dict[str, Any]] = {}


def get_translations(lang: str = "en") -> Dict[str, Any]:
    """
    Carrega traduções de um arquivo JSON com cache em memória.

    Args:
        lang: Código do idioma ('en' ou 'pt'). Padrão: 'en'.

    Returns:
        Dicionário com traduções (pode conter sub-dicionários).
    """
    if lang in _translations_cache:
        return _translations_cache[lang]

    # Tentar múltiplos caminhos para o arquivo de traduções
    possible_paths = [
        os.path.join("config", "translations", f"{lang}.json"),
        os.path.join("/app", "config", "translations", f"{lang}.json"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "translations",
            f"{lang}.json",
        ),
    ]

    for file_path in possible_paths:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    translations = json.load(f)
                    _translations_cache[lang] = translations
                    logger.info(
                        f"✅ Traduções '{lang}' carregadas de: {file_path}"
                    )
                    return translations
            except json.JSONDecodeError:
                logger.error(f"❌ Erro de sintaxe no JSON: {file_path}")
                return {}

    # Fallback: se não encontrou o idioma solicitado, tenta inglês
    logger.warning(
        f"⚠️ Tradução '{lang}' não encontrada. Tentando fallback 'en'."
    )
    if lang != "en":
        return get_translations("en")

    logger.error("❌ Arquivo de tradução padrão 'en.json' não encontrado.")
    return {}


def t(lang: str, *keys: str, default: str = "") -> str:
    """
    Acessa tradução por caminho de chaves aninhadas.

    Args:
        lang: Código do idioma ('en' ou 'pt')
        *keys: Caminho de chaves (ex: "sidebar", "title")
        default: Valor padrão se chave não encontrada

    Returns:
        String traduzida ou default

    Exemplos:
        t("pt", "sidebar", "title")         → "Calculadora ETo"
        t("en", "navbar", "home")            → "HOME"
        t("pt", "results", "success_days")   → "dias calculados"
        t("en", "inexistente", default="?")  → "?"
    """
    translations = get_translations(lang)
    value = translations

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default

    return value if isinstance(value, str) else default


def clear_translations_cache():
    """Limpa cache de traduções (útil para hot-reload em dev)."""
    global _translations_cache
    _translations_cache = {}
    logger.info("🔄 Cache de traduções limpo")
