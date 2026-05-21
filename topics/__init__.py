"""
topics/ — One file per discussion topic.

Each topic file defines:
  TOPIC_NAME  : str           — matches the filename (e.g. "immigration")
  TOPIC_LABEL : str           — full string used in prompts (e.g. "immigration policy")
  PERSONAS    : list[dict]    — agent definitions (see immigration.py for the schema)

personas.py imports from here based on the TOPIC env var.
"""
