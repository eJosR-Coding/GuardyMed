from apps.api.app.core.config import settings
from apps.api.app.domain.scheduling.repository import InMemorySchedulingRepository
from apps.api.app.domain.scheduling.sqlalchemy_repository import SQLAlchemySchedulingRepository
from apps.api.app.domain.scheduling.service import SchedulingService
from apps.api.app.infra.db import init_db, make_session_factory


if settings.persistence_backend == "sqlalchemy":
    engine, session_factory = make_session_factory(settings.database_url)
    init_db(engine)
    repository = SQLAlchemySchedulingRepository(session_factory)
else:
    repository = InMemorySchedulingRepository()

service = SchedulingService(repository)
