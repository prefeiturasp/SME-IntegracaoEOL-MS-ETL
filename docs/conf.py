"""Sphinx configuration."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "SME-SGP-MS-ETL"
author = "Equipe SME"
release = "1.0.0"
language = "pt_BR"

extensions = [
    "myst_parser",
    "sphinx.ext.graphviz",
    "sphinx.ext.autosectionlabel",
]

autosectionlabel_prefix_document = True

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_title = "SME-SGP-MS-ETL"
html_short_title = "ETL Docs"
graphviz_output_format = "svg"
