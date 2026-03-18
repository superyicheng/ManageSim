"""Data sanitization pipeline — 7-step cleaning for agent-generated text."""

import re

# Patterns to strip
FILE_PATH_PATTERN = re.compile(r'(?:/[a-zA-Z0-9._-]+){3,}')
URL_PATTERN = re.compile(r'https?://\S+')
LLM_ARTIFACT_PATTERN = re.compile(r'```(?:json|python|bash|yaml)?\s*\n.*?\n```', re.DOTALL)
CONVERSATION_HEADER_PATTERN = re.compile(r'^(Human|Assistant|System):.*$', re.MULTILINE)
WHITESPACE_PATTERN = re.compile(r'\s+')

JUNK_STRINGS = {"ok", "yes", "no", "?", "...", "done", "sure", "thanks", "ty", "k"}

MAX_TITLE_LENGTH = 80
MAX_SUMMARY_LENGTH = 500
MIN_TITLE_LENGTH = 6


def strip_file_paths(text):
    return FILE_PATH_PATTERN.sub('[path]', text)

def strip_urls(text):
    return URL_PATTERN.sub('[url]', text)

def strip_llm_artifacts(text):
    return LLM_ARTIFACT_PATTERN.sub('', text)

def strip_conversation_headers(text):
    return CONVERSATION_HEADER_PATTERN.sub('', text)

def collapse_whitespace(text):
    return WHITESPACE_PATTERN.sub(' ', text).strip()

def validate_title(title):
    clean = title.strip()
    if len(clean) < MIN_TITLE_LENGTH:
        return None, f"Title too short (min {MIN_TITLE_LENGTH} chars): '{clean}'"
    if clean.lower() in JUNK_STRINGS:
        return None, f"Junk title rejected: '{clean}'"
    return clean, None

def truncate(text, max_length):
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def sanitize_title(raw_title):
    """Full 7-step sanitization for titles."""
    text = raw_title
    text = strip_file_paths(text)
    text = strip_urls(text)
    text = strip_llm_artifacts(text)
    text = strip_conversation_headers(text)
    text = collapse_whitespace(text)
    clean, error = validate_title(text)
    if error:
        return None, error
    return truncate(clean, MAX_TITLE_LENGTH), None

def sanitize_summary(raw_summary):
    """Full 7-step sanitization for summaries."""
    text = raw_summary
    text = strip_file_paths(text)
    text = strip_urls(text)
    text = strip_llm_artifacts(text)
    text = strip_conversation_headers(text)
    text = collapse_whitespace(text)
    if not text or len(text.strip()) < 3:
        return None, "Summary too short"
    return truncate(text, MAX_SUMMARY_LENGTH), None

def sanitize_body(raw_body):
    """Light sanitization for body text (preserve more content)."""
    text = strip_conversation_headers(raw_body)
    text = collapse_whitespace(text)
    return text
