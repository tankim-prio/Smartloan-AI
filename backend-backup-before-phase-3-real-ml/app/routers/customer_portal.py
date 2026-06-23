from fastapi import APIRouter
from pydantic import EmailStr

from app.core.customer_db import init_customer_db
from app.schemas.customer_portal import (
    CustomerRegisterRequest,
    CustomerLoginRequest,
    CustomerApplicationRequest,
)
from app.services.customer_portal_service import (
    health_status,
    register_customer,
    login_customer,
    list_customers,
    create_customer_application,
    list_customer_applications,
)


router = APIRouter(prefix="/api/v1/customer-portal", tags=["Customer Portal"])


@router.on_event("startup")
def startup():
    init_customer_db()


@router.get("/health")
def health():
    return health_status()


@router.post("/register")
def register(data: CustomerRegisterRequest):
    return register_customer(data)


@router.post("/login")
def login(data: CustomerLoginRequest):
    return login_customer(data)


@router.get("/customers")
def customers():
    return list_customers()


@router.post("/applications")
def applications_create(data: CustomerApplicationRequest):
    return create_customer_application(data)


@router.get("/applications")
def applications_list(email: EmailStr):
    return list_customer_applications(str(email))
