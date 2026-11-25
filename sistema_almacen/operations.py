"""Reglas transaccionales del inventario. Nunca se acepta un saldo calculado por el navegador."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models as m
from . import schemas as s


def milli(v):
    return int(Decimal(v) * 1000)


def cents(v):
    return int(Decimal(v) * 100)


def quantity(v):
    return v / 1000


def amount(v):
    return v / 100


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')


def get(db, cls, key):
    obj = db.get(cls, key)
    if obj is None:
        raise HTTPException(404, 'Registro no encontrado.')
    return obj


def product_dict(p):
    return dict(id=p.id, code=p.code, name=p.name, category=p.category, detail=p.detail,
                unit=p.unit, stock=quantity(p.stock), min=quantity(p.minimum), cost=amount(p.cost),
                location=p.location, supplier=p.supplier)


def movement_dict(x):
    return dict(id=x.id, productId=x.product_id, code=x.code, name=x.name, type=x.type,
                qty=quantity(x.qty), unit=x.unit, cost=amount(x.cost), when=x.when,
                note=x.note, order=x.order, operator=x.operator)


def order_dict(o):
    return dict(id=o.id, code=o.code, name=o.name, client=o.client, state=o.state,
                budget=amount(o.budget), workshopOrderId=o.workshop_order_id)


def supplier_dict(x):
    return dict(id=x.id, name=x.name, phone=x.phone, email=x.email, notes=x.notes)


def snapshot(db: Session):
    revision = db.get(m.InventoryRevision, 1).revision
    return dict(revision=revision,
                products=[product_dict(p) for p in db.scalars(select(m.Product).order_by(m.Product.code))],
                movements=[movement_dict(x) for x in db.scalars(select(m.Movement).order_by(m.Movement.when.desc(),m.Movement.id.desc()))],
                orders=[order_dict(o) for o in db.scalars(select(m.WorkOrder).order_by(m.WorkOrder.code))],
                suppliers=[supplier_dict(x) for x in db.scalars(select(m.Supplier).order_by(m.Supplier.name))])


def unique_code(db, cls, code, exclude=None):
    found = db.scalar(select(cls).where(cls.code == code))
    if found and found.id != exclude:
        raise HTTPException(409, f'El código {code} ya está registrado.')


def record(db, p, kind, qty, note='', order='', operator='Operador'):
    db.add(m.Movement(id=str(uuid4()), product_id=p.id, code=p.code, name=p.name,
                      type=kind, qty=qty, unit=p.unit, cost=p.cost, when=utc_now(),
                      note=note, order=order, operator=operator))


def make_product(v, key=None):
    return m.Product(id=key or str(uuid4()), code=v.code, name=v.name, category=v.category,
                     detail=v.detail, unit=v.unit, stock=milli(v.stock), minimum=milli(v.min),
                     cost=cents(v.cost), location=v.location, supplier=v.supplier)


def create_product(db, v:s.ProductInput):
    unique_code(db,m.Product,v.code)
    p=make_product(v)
    db.add(p)
    db.flush()
    if p.stock:
        record(db,p,'entrada',p.stock,'Stock inicial')


def edit_product(db,key,v:s.ProductInput):
    p=get(db,m.Product,key)
    unique_code(db,m.Product,v.code,key)
    if p.stock!=milli(v.stock):
        raise HTTPException(409,'Para modificar existencias, registra un ajuste o movimiento.')
    if p.unit!=v.unit and (p.stock or db.scalar(select(m.Movement.id).where(m.Movement.product_id==p.id).limit(1))):
        raise HTTPException(409,'No se puede cambiar la unidad de un material con stock o historial.')
    for k in ('code','name','category','detail','unit','location','supplier'):
        setattr(p,k,getattr(v,k))
    p.minimum=milli(v.min);p.cost=cents(v.cost)


def move(db,v:s.MovementInput):
    p=get(db,m.Product,v.productId)
    q=milli(v.qty);note=v.note;order=v.order
    if order:
        o=db.scalar(select(m.WorkOrder).where(m.WorkOrder.code==order))
        if not o: raise HTTPException(400,'La orden de trabajo no existe.')
        order=o.code
    if v.type=='traslado':
        if not v.location: raise HTTPException(400,'Ingresa una ubicación de destino.')
        note=f'{p.location or "Sin asignar"} → {v.location}. {note}'
        p.location=v.location;q=0
    elif v.type=='ajuste':
        note=f'Saldo anterior: {quantity(p.stock):g}; nuevo saldo: {quantity(q):g}. {note}'
        p.stock=q
    else:
        if q<=0: raise HTTPException(400,'Ingresa una cantidad mayor a cero.')
        if v.type in ('salida','merma'):
            if q>p.stock: raise HTTPException(409,'Stock insuficiente.')
            p.stock-=q
        else:
            if p.stock+q>10**12: raise HTTPException(400,'El saldo excede el límite permitido.')
            p.stock+=q
    record(db,p,v.type,q,note,order,v.operator)


def remnant(db,key,v:s.RemnantInput):
    p=get(db,m.Product,key);unique_code(db,m.Product,v.code)
    q=milli(v.qty)
    if q<=0 or q>p.stock: raise HTTPException(409,'Cantidad no disponible.')
    new=m.Product(id=str(uuid4()),code=v.code,name=(p.name[:108]+' · Sobrante'),category=p.category,
                  detail=v.detail,unit=p.unit,stock=q,minimum=0,cost=p.cost,location=v.location,supplier=p.supplier)
    p.stock-=q;db.add(new);db.flush()
    record(db,p,'ajuste',p.stock,f'Separación {quantity(q):g} {p.unit} hacia {new.code}')
    record(db,new,'entrada',q,f'Sobrante de {p.code}')


def create_order(db,v:s.OrderInput):
    unique_code(db,m.WorkOrder,v.code)
    db.add(m.WorkOrder(id=str(uuid4()),code=v.code,name=v.name,client=v.client,state=v.state,budget=cents(v.budget)))


def edit_order(db,key,v:s.OrderInput):
    o=get(db,m.WorkOrder,key)
    if v.code!=o.code: raise HTTPException(400,'El código de la orden no se puede cambiar.')
    o.name=v.name;o.client=v.client;o.state=v.state;o.budget=cents(v.budget)


def save_supplier(db,v:s.SupplierInput,key=None):
    found=db.scalar(select(m.Supplier).where(m.Supplier.name==v.name))
    if found and found.id!=key: raise HTTPException(409,'Ya existe ese proveedor.')
    if key:
        obj=get(db,m.Supplier,key)
        for p in db.scalars(select(m.Product).where(m.Product.supplier==obj.name)):
            p.supplier=v.name
        for k,val in v.model_dump().items(): setattr(obj,k,val)
    else:
        db.add(m.Supplier(id=str(uuid4()),**v.model_dump()))


def restore(db,v:s.Backup):
    # Validaciones previas al reemplazo; una excepción revierte la transacción completa.
    for rows,attr in ((v.products,'code'),(v.orders,'code'),(v.suppliers,'name')):
        values=[getattr(x,attr).casefold() for x in rows]
        if len(set(values))!=len(values): raise HTTPException(400,'La copia contiene códigos o nombres duplicados.')
    for rows in (v.products,v.orders,v.suppliers,v.movements):
        if len({x.id for x in rows})!=len(rows): raise HTTPException(400,'La copia contiene identificadores duplicados.')
    products={x.id for x in v.products};orders={x.code for x in v.orders}
    if any(x.productId not in products or (x.order and x.order not in orders) for x in v.movements):
        raise HTTPException(400,'La copia contiene movimientos sin material u orden válida.')
    for cls in (m.Movement,m.Product,m.WorkOrder,m.Supplier): db.execute(delete(cls))
    for p in v.products: db.add(make_product(p,p.id))
    for o in v.orders: db.add(m.WorkOrder(id=o.id,code=o.code,name=o.name,client=o.client,state=o.state,budget=cents(o.budget),workshop_order_id=o.workshopOrderId))
    for x in v.suppliers: db.add(m.Supplier(**x.model_dump()))
    db.flush()
    for x in v.movements:
        db.add(m.Movement(id=x.id,product_id=x.productId,code=x.code,name=x.name,type=x.type,qty=milli(x.qty),unit=x.unit,cost=cents(x.cost),when=x.when.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'),note=x.note,order=x.order,operator=x.operator))
