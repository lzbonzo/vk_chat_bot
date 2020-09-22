from pony.orm import Database, Required, Json
from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """Состояние пользователя внутри сценария"""
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)
    do_continue = True


class Registration(db.Entity):
    """Данные для бронирования"""
    user_id = Required(str)
    From = Required(str)
    to = Required(str)
    date = Required(str)
    seats = Required(str)
    flight = Required(str)
    comment = Required(str)
    phone = Required(str)


db.generate_mapping(create_tables=True)
