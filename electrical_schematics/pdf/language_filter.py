"""Language filtering utilities for bilingual PDF extraction.

This module provides utilities to detect and filter German text from
bilingual industrial PDFs that contain both English and German designations.
"""

from typing import List

# Common German technical terms found in industrial documentation
GERMAN_TECHNICAL_TERMS = {
    # Control & automation
    'Steuerung', 'steuerung',
    'Schütz', 'schutz', 'Schütz',
    'Relais', 'relais',
    'Relaismodul', 'relaismodul',
    'Hilfsblock', 'hilfsblock',
    'Betriebsmittel', 'betriebsmittel',

    # Protection & safety
    'Sicherung', 'sicherung',
    'Sicherungsautomat', 'sicherungsautomat',
    'Schutzschalter', 'schutzschalter',

    # Power & motors
    'Frequenzumrichter', 'frequenzumrichter',
    'Stromversorgung', 'stromversorgung',
    'Netzteil', 'netzteil',
    'Drehstrommotor', 'drehstrommotor',
    'Bremsgleichrichter', 'bremsgleichrichter',

    # Mechanical
    'Lüfter', 'lufter', 'Lufter',
    'Ventilator', 'ventilator',
    'Inkrementalgeber', 'inkrementalgeber',  # Incremental encoder

    # Electrical components
    'Widerstand', 'widerstand',
    'Kondensator', 'kondensator',
    'Spule', 'spule',

    # Filters & interference
    'EMV-Filter', 'emv-filter',
    'Netzfilter', 'netzfilter',
    'Entstörfilter', 'entstorfilter',

    # Connections & terminals
    'Anschluss', 'anschluss',
    'Klemme', 'klemme',
    'Klemmleiste', 'klemmleiste',

    # Expansion & accessories
    'Kontakterweiterung', 'kontakterweiterung',
    'Erweiterung', 'erweiterung',
    'Zusatz', 'zusatz',

    # Time & delay
    'verzögert', 'verzogert',
    'Zeitrelais', 'zeitrelais',

    # Common prefixes/suffixes
    'Bezeichnung',  # "Designation" header in German
    'Betriebsmittelkennzeichen',  # "Device tag" in German
}


def contains_german_term(text: str) -> bool:
    """Check if text contains German technical terms.

    Args:
        text: Text to check

    Returns:
        True if German terms are detected
    """
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in GERMAN_TECHNICAL_TERMS)


def is_likely_german_line(text: str) -> bool:
    """Determine if a line is likely German-only text.

    This is stricter than contains_german_term - it checks if the line
    is primarily German without English equivalents.

    Args:
        text: Text to check

    Returns:
        True if line appears to be German-only
    """
    if not text or len(text.strip()) < 2:
        return False

    # Check for German-only terms (not shared with English)
    german_only_terms = [
        'Steuerung', 'steuerung',
        'Schütz', 'schutz',
        'Relaismodul', 'relaismodul',
        'Hilfsblock', 'hilfsblock',
        'Sicherungsautomat', 'sicherungsautomat',
        'Frequenzumrichter', 'frequenzumrichter',
        'Drehstrommotor', 'drehstrommotor',
        'Stromversorgung', 'stromversorgung',
        'Lüfter', 'lufter', 'Lufter',
        'Widerstand', 'widerstand',
        'EMV-Filter', 'emv-filter',
        'Kontakterweiterung', 'kontakterweiterung',
        'Inkrementalgeber', 'inkrementalgeber',
        'Bremsgleichrichter', 'bremsgleichrichter',
        'verzögert', 'verzogert',
        'Bezeichnung', 'bezeichnung',
    ]

    text_lower = text.lower()
    return any(term.lower() in text_lower for term in german_only_terms)


def filter_german_from_text(text: str, separator: str = ' ') -> str:
    """Remove German words from bilingual text.

    Args:
        text: Bilingual text containing both English and German
        separator: Separator used between words (default: space)

    Returns:
        Text with German words removed
    """
    if not text:
        return text

    words = text.split(separator)
    english_words = []

    for word in words:
        word_stripped = word.strip()
        # Skip empty words
        if not word_stripped:
            continue
        # Skip if word is a German-only term
        if not is_likely_german_line(word_stripped):
            english_words.append(word_stripped)

    result = separator.join(english_words).strip()

    # Remove duplicate consecutive words (e.g., "Circuit breaker Circuit breaker" -> "Circuit breaker")
    result_words = result.split()
    deduplicated = []
    prev_word = None
    for word in result_words:
        if word.lower() != (prev_word.lower() if prev_word else None):
            deduplicated.append(word)
        prev_word = word

    return ' '.join(deduplicated)


def select_english_from_alternates(texts: List[str]) -> str:
    """Select English text from a list of alternating English/German texts.

    In bilingual PDFs, designations often appear as pairs:
    - Line 1: English term
    - Line 2: German term

    This function selects the non-German option.

    Args:
        texts: List of text alternatives

    Returns:
        English text, or first non-German text
    """
    if not texts:
        return ''

    # Filter out German-only lines
    english_texts = [t for t in texts if not is_likely_german_line(t)]

    if english_texts:
        return ' '.join(english_texts)

    # Fallback: return first text if all appear to be German
    return texts[0] if texts else ''
