# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "DiTTo"
copyright = "2024, National Renewable Energy Laboratory"
author = "Tarek Elgindy, Aadil Latif, Kapil Duwadi, Daniel Thompson, Jeremy Keen"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.autodoc_pydantic",
    "sphinxcontrib.mermaid",
]
# templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "pydata_sphinx_theme"
# html_static_path = ["_static"]

source_suffix = [".md"]
myst_enable_extensions = ["colon_fence"]
