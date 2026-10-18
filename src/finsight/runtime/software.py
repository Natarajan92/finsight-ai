"""Installed versions used in run and index replay identities; no provider imports."""

from importlib.metadata import version


def software_versions() -> dict[str, str]:
    packages = (
        "langchain-core",
        "langchain-anthropic",
        "langchain-chroma",
        "chromadb",
        "tokenizers",
        "httpx",
        "anthropic",
        "langsmith",
        "pydantic",
        "PyMuPDF",
    )
    return {name: version(name) for name in packages}
