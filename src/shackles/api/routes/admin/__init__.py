"""Admin route package — aggregates all admin sub-routers."""

from fastapi import APIRouter

from shackles.api.routes.admin import (
    accommodations as accommodation_routes,
    dashboard as dashboard_routes,
    events as event_routes,
    exports as export_routes,
    id_cards as id_card_routes,
    marking as marking_routes,
    messages as message_routes,
    papers as paper_routes,
    payments as payment_routes,
    permissions as permission_routes,
    registrations as registration_routes,
    staff as staff_routes,
    teams as team_routes,
    users as user_routes,
)


admin_router = APIRouter(prefix="/admin", tags=["admin"])

admin_router.include_router(dashboard_routes.router)
admin_router.include_router(user_routes.router)
admin_router.include_router(event_routes.router)
admin_router.include_router(payment_routes.router)
admin_router.include_router(registration_routes.router)
admin_router.include_router(team_routes.router)
admin_router.include_router(marking_routes.router)
admin_router.include_router(paper_routes.router)
admin_router.include_router(staff_routes.router)
admin_router.include_router(permission_routes.router)
admin_router.include_router(accommodation_routes.router)
admin_router.include_router(message_routes.router)
admin_router.include_router(export_routes.router)
admin_router.include_router(id_card_routes.router)