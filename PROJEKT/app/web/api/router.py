from fastapi import APIRouter

from app.web.api import audit, auth, base_dashboard, ip_addresses, mail_addresses, organizations, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(base_dashboard.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(mail_addresses.router)
api_router.include_router(ip_addresses.router)
api_router.include_router(audit.router)
