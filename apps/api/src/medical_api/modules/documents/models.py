"""Document metadata shared across modules (consent PDFs, exports).

Concrete document rows currently live next to their owning module
(e.g. `medical_api.modules.consents.models.ConsentDocument`) to keep
foreign keys within a single bounded context. This module is the place
for cross-cutting document concerns as they emerge (e.g. export bundles).
"""
