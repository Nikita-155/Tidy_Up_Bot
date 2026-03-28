from sqlalchemy import *
from sqlalchemy.orm import *
from datetime import datetime
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    orders = relationship("Order", back_populates="client")


class Cleaner(Base):
    __tablename__ = "cleaners"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    status = Column(String, default="inactive")
    completed_orders = Column(Integer, default=0)
    cancelled_orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    orders = relationship("Order", back_populates="cleaner")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    telegram_id = Column(Integer, unique=True)
    role = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cleaner_id = Column(Integer, ForeignKey("cleaners.id"), nullable=True)

    cleaning_type = Column(String, nullable=False)
    area = Column(Float, nullable=False)
    address = Column(String, nullable=False)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    photos = Column(Text, nullable=True)

    status = Column(String, default="new")

    created_at = Column(DateTime, default=datetime.now)
    accepted_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    client = relationship("User", back_populates="orders")
    cleaner = relationship("Cleaner", back_populates="orders")


Base.metadata.create_all(bind=engine)


def _run_migrations():
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(cleaners)"))
            cols = [row[1] for row in result.fetchall()]
            if "completed_orders" not in cols:
                conn.execute(text("ALTER TABLE cleaners ADD COLUMN completed_orders INTEGER DEFAULT 0"))
            if "cancelled_orders" not in cols:
                conn.execute(text("ALTER TABLE cleaners ADD COLUMN cancelled_orders INTEGER DEFAULT 0"))
            if "created_at" not in cols:
                conn.execute(text("ALTER TABLE cleaners ADD COLUMN created_at DATETIME"))


            result = conn.execute(text("PRAGMA table_info(orders)"))
            cols = [row[1] for row in result.fetchall()]
            if "photos" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN photos TEXT"))
            if "accepted_at" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN accepted_at DATETIME"))
            if "started_at" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN started_at DATETIME"))
            if "completed_at" not in cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN completed_at DATETIME"))
    except Exception:
        pass


_run_migrations()


# ==================== ПОЛЬЗОВАТЕЛИ ====================
def get_user(telegram_id):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    session.close()
    return user


def get_user_by_id(user_id):
    session = SessionLocal()
    user = session.query(User).filter_by(id=user_id).first()
    session.close()
    return user


def create_user(telegram_id, username, first_name):
    session = SessionLocal()
    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    session.commit()
    session.close()
    return user


def update_user_phone(telegram_id, phone):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        user.phone = phone
        session.commit()
    session.close()


# ==================== УБОРЩИКИ ====================
def get_cleaner(user_id):
    session = SessionLocal()
    cleaner = session.query(Cleaner).filter_by(user_id=user_id).first()
    session.close()
    return cleaner


def get_cleaner_by_id(cleaner_id):
    session = SessionLocal()
    cleaner = session.query(Cleaner).filter_by(id=cleaner_id).first()
    session.close()
    return cleaner


def create_cleaner(user_id, full_name, phone):
    session = SessionLocal()
    cleaner = Cleaner(user_id=user_id, full_name=full_name, phone=phone)
    session.add(cleaner)
    session.commit()
    session.close()
    return cleaner


def update_cleaner_status(cleaner_id, status):
    session = SessionLocal()
    cleaner = session.query(Cleaner).filter_by(id=cleaner_id).first()
    if cleaner:
        cleaner.status = status
        session.commit()
    session.close()


def update_cleaner_info(cleaner_id, full_name=None, phone=None):
    session = SessionLocal()
    cleaner = session.query(Cleaner).filter_by(id=cleaner_id).first()
    if cleaner:
        if full_name:
            cleaner.full_name = full_name
        if phone:
            cleaner.phone = phone
        session.commit()
    session.close()


def get_all_cleaners():
    session = SessionLocal()
    cleaners = session.query(Cleaner).all()
    session.close()
    return cleaners


# ==================== АДМИНИСТРАТОРЫ ====================
def get_all_admins():
    session = SessionLocal()
    admins = session.query(Admin).all()
    session.close()
    return admins


def get_admin_notify_telegram_ids():
    from config import ADMIN_IDS
    ids = set(ADMIN_IDS)
    session = SessionLocal()
    for adm in session.query(Admin).all():
        if adm.telegram_id is not None:
            ids.add(adm.telegram_id)
    session.close()
    return ids


def create_admin(user_id, telegram_id, role="admin"):
    session = SessionLocal()
    admin = Admin(user_id=user_id, telegram_id=telegram_id, role=role)
    session.add(admin)
    session.commit()
    session.close()
    return admin


def get_admin(telegram_id):
    session = SessionLocal()
    admin = session.query(Admin).filter_by(telegram_id=telegram_id).first()
    session.close()
    return admin


# ==================== ЗАКАЗЫ ====================
def create_order(client_id, order_data):
    session = SessionLocal()
    order = Order(client_id=client_id, **order_data)
    session.add(order)
    session.commit()
    session.close()
    return order


def get_order(order_id):
    session = SessionLocal()
    order = session.query(Order).filter_by(id=order_id).first()
    session.close()
    return order


def get_user_orders(telegram_id):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    orders = []
    if user:
        orders = session.query(Order).filter_by(client_id=user.id).order_by(Order.created_at.desc()).all()
    session.close()
    return orders


def get_all_orders():
    session = SessionLocal()
    orders = session.query(Order).order_by(Order.created_at.desc()).all()
    session.close()
    return orders


def get_available_orders():
    session = SessionLocal()
    orders = session.query(Order).filter_by(status="new").all()
    session.close()
    return orders


def get_cleaner_orders(cleaner_id):
    session = SessionLocal()
    orders = session.query(Order).filter(
        Order.cleaner_id == cleaner_id,
        Order.status.in_(["accepted", "in_progress"])
    ).all()
    session.close()
    return orders


def assign_order(order_id, cleaner_id):
    session = SessionLocal()
    order = session.query(Order).filter_by(id=order_id, status="new").first()
    if order:
        order.cleaner_id = cleaner_id
        order.status = "accepted"
        order.accepted_at = datetime.now()
        session.commit()
        session.close()
        return True
    session.close()
    return False


def update_order_status(order_id, status):
    session = SessionLocal()
    order = session.query(Order).filter_by(id=order_id).first()
    if order:
        order.status = status
        if status == "in_progress":
            order.started_at = datetime.now()
        elif status == "completed":
            order.completed_at = datetime.now()
        session.commit()
    session.close()


def complete_order(order_id, photos):
    session = SessionLocal()
    order = session.query(Order).filter_by(id=order_id).first()
    if order:
        order.status = "completed"
        order.photos = ",".join(photos)
        order.completed_at = datetime.now()
        if order.cleaner_id:
            cleaner = session.query(Cleaner).filter_by(id=order.cleaner_id).first()
            if cleaner:
                cleaner.completed_orders += 1
        session.commit()
    session.close()


def clear_all_orders():
    from sqlalchemy import text
    session = SessionLocal()
    try:
        session.query(Order).delete()
        session.query(Cleaner).update({Cleaner.completed_orders: 0}, synchronize_session=False)
        session.commit()
    finally:
        session.close()
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name='orders'"))
    except Exception:
        pass