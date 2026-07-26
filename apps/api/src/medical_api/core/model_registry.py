"""Imports every module's models so `Base.metadata` is fully populated for
Alembic autogenerate. Import this module (not the individual model modules)
wherever the complete metadata is needed.
"""

from medical_api.modules.audit import models as _audit_models  # noqa: F401
from medical_api.modules.consents import models as _consents_models  # noqa: F401
from medical_api.modules.identity import models as _identity_models  # noqa: F401
from medical_api.modules.medical_records import models as _medical_records_models  # noqa: F401
from medical_api.modules.notifications import models as _notifications_models  # noqa: F401
from medical_api.modules.organizations import models as _organizations_models  # noqa: F401
from medical_api.modules.patients import models as _patients_models  # noqa: F401
from medical_api.modules.scheduling import models as _scheduling_models  # noqa: F401
from medical_api.modules.treatments import models as _treatments_models  # noqa: F401
