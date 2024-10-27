from ninja import NinjaAPI

from domovoy.apps.dmv_user.api.v1.api import users_v1_router
from domovoy.apps.dmv_home.api.v1.api import homes_v1_router

from domovoy.apps.regular_job.api.v1.api import regular_jobs_v1_router

api = NinjaAPI(title="Domovoy API")

api.add_router("users/v1/", users_v1_router)
api.add_router("homes/v1/", homes_v1_router)
api.add_router("regular_jobs/v1/", regular_jobs_v1_router)
