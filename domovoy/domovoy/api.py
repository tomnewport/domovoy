from ninja import NinjaAPI

from domovoy.apps.dmv_user.api.v1.api import users_v1_router

api = NinjaAPI(title="Domovoy API")

api.add_router('users/v1/', users_v1_router)
