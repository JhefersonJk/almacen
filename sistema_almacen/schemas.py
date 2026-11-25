"""Contratos de la API y formato de respaldo compatible con la versión 0.2."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Quantity = Annotated[Decimal, Field(ge=0, le=1000000000, decimal_places=3)]
Money = Annotated[Decimal, Field(ge=0, le=1000000000, decimal_places=2)]
Code = Annotated[str, Field(min_length=1, max_length=48, pattern=r'^[\x20-\x7e]+$')]
Identifier = Annotated[str, Field(min_length=1, max_length=80)]
Category = Literal['Papel','Vinilo','Lona','Tintas','Planchas','Laminados','Repuestos','Otros']
Unit = Literal['hojas','resmas','m','m²','L','ml','planchas','unidades','kg']
MovementType = Literal['entrada','salida','devolucion','ajuste','traslado','merma']


class Contract(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)


class ProductInput(Contract):
    code: Code
    name: str = Field(min_length=1, max_length=120)
    category: Category
    detail: str = Field(default='', max_length=120)
    unit: Unit
    stock: Quantity = Decimal(0)
    min: Quantity = Decimal(0)
    cost: Money = Decimal(0)
    location: str = Field(default='', max_length=50)
    supplier: str = Field(default='', max_length=160)


class ProductBackup(ProductInput):
    id: Identifier


class MovementInput(Contract):
    productId: Identifier
    type: MovementType
    qty: Quantity = Decimal(0)
    location: str = Field(default='', max_length=50)
    order: str = Field(default='', max_length=80)
    operator: str = Field(default='Operador', min_length=1, max_length=60)
    note: str = Field(default='', max_length=2000)


class RemnantInput(Contract):
    code: Code
    qty: Quantity
    detail: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=50)


class OrderInput(Contract):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    client: str = Field(default='', max_length=160)
    state: Literal['Pendiente','En producción','Finalizada']
    budget: Money = Decimal(0)


class OrderBackup(OrderInput):
    id: Identifier
    workshopOrderId: str | None = Field(default=None,max_length=80)


class SupplierInput(Contract):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(default='', max_length=60)
    email: str = Field(default='', max_length=254)
    notes: str = Field(default='', max_length=2000)


class SupplierBackup(SupplierInput):
    id: Identifier


class MovementBackup(Contract):
    id: Identifier
    productId: Identifier
    code: Code
    name: str = Field(min_length=1,max_length=150)
    type: MovementType
    qty: Quantity
    unit: Unit
    cost: Money
    when: datetime
    note: str = Field(default='',max_length=2000)
    order: str = Field(default='',max_length=80)
    operator: str = Field(default='Operador',max_length=60)

    @field_validator('when')
    @classmethod
    def require_timezone(cls,value):
        if value.tzinfo is None:
            raise ValueError('La fecha del movimiento requiere zona horaria.')
        return value


class Backup(Contract):
    products: list[ProductBackup] = Field(max_length=25000)
    movements: list[MovementBackup] = Field(max_length=250000)
    orders: list[OrderBackup] = Field(max_length=25000)
    suppliers: list[SupplierBackup] = Field(max_length=25000)
