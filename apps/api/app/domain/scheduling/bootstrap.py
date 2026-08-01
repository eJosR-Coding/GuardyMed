from apps.api.app.domain.scheduling.repository import InMemorySchedulingRepository
from apps.api.app.domain.scheduling.service import SchedulingService


repository = InMemorySchedulingRepository()
service = SchedulingService(repository)
