"""tracegate core: the IP layer.

Everything that is NOT commodity lives here: the catalog model, traceability-ID
derivation, the drift-gate engine, the markdown + JSON renderers, and zero-config
stack detection. Adapters (under `tracegate.adapters`) feed this core; the core
does not know about any specific language or framework.
"""
