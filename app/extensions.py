from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from flask_bootstrap import Bootstrap4
from flask_rq2 import RQ
from flask_session import Session

db = SQLAlchemy()
login_manager = LoginManager()
scheduler = APScheduler()
bootstrap = Bootstrap4()
rq = RQ()
session = Session()
