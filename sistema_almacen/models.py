"""Tablas del almacén. Cantidades en milésimas y costos en centavos, sin deriva binaria."""
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class InventoryRevision(Base):
    __tablename__ = 'inventory_revision'
    id: Mapped[int] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Product(Base):
    __tablename__ = 'inventory_products'
    __table_args__ = (CheckConstraint('stock >= 0 AND minimum >= 0 AND cost >= 0'),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    code: Mapped[str] = mapped_column(String(48, collation='NOCASE'), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str] = mapped_column(String(120), default='')
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    minimum: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str] = mapped_column(String(50), default='')
    supplier: Mapped[str] = mapped_column(String(160), default='')


class WorkOrder(Base):
    __tablename__ = 'inventory_work_orders'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    code: Mapped[str] = mapped_column(String(80, collation='NOCASE'), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    client: Mapped[str] = mapped_column(String(160), default='')
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    budget: Mapped[int] = mapped_column(Integer, default=0)
    # Futuro: identificador del pedido original en Gráfica Ali, sin vincular automáticamente.
    workshop_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)


class Supplier(Base):
    __tablename__ = 'inventory_suppliers'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160, collation='NOCASE'), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(60), default='')
    email: Mapped[str] = mapped_column(String(254), default='')
    notes: Mapped[str] = mapped_column(Text, default='')


class Movement(Base):
    __tablename__ = 'inventory_movements'
    __table_args__ = (CheckConstraint('qty >= 0 AND cost >= 0'),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey('inventory_products.id'), index=True)
    # Snapshot para conservar el nombre, unidad y precio al momento del movimiento.
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    when: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    note: Mapped[str] = mapped_column(Text, default='')
    order: Mapped[str] = mapped_column(String(80), default='', index=True)
    operator: Mapped[str] = mapped_column(String(60), default='Operador')
