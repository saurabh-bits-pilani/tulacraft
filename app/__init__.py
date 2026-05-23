from flask import Flask, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from dotenv import load_dotenv
from sqlalchemy import text
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    # Railway gives postgres:// but SQLAlchemy 2.0 requires postgresql://
    db_url = os.getenv("DATABASE_URL", "sqlite:///craftbridge.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "producer.login"

    from app.routes.producer import producer_bp
    from app.routes.buyer import buyer_bp
    from app.routes.api import api_bp
    from app.routes.shop import shop_bp

    app.register_blueprint(producer_bp, url_prefix="/producer")
    app.register_blueprint(buyer_bp, url_prefix="/shop")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(shop_bp, url_prefix="/shop")

    from app.models import Producer, Buyer

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith("p_"):
            return Producer.query.get(int(user_id[2:]))
        elif user_id.startswith("b_"):
            return Buyer.query.get(int(user_id[2:]))
        return None

    @app.route("/")
    def index():
        return redirect(url_for("buyer.shop"))

    @app.context_processor
    def inject_unread_counts():
        from app.models import Lead, Message
        buyer_unread = 0
        producer_unread = 0
        try:
            buyer_id = session.get("buyer_id")
            if buyer_id:
                lead_ids = [l.id for l in Lead.query.filter_by(buyer_id=buyer_id).all()]
                if lead_ids:
                    buyer_unread = Message.query.filter(
                        Message.lead_id.in_(lead_ids),
                        Message.sender_type == "producer",
                        Message.read_at.is_(None)
                    ).count()
            if current_user.is_authenticated and hasattr(current_user, "products"):
                lead_ids = [l.id for l in Lead.query.filter_by(producer_id=current_user.id).all()]
                if lead_ids:
                    producer_unread = Message.query.filter(
                        Message.lead_id.in_(lead_ids),
                        Message.sender_type == "buyer",
                        Message.read_at.is_(None)
                    ).count()
        except Exception:
            pass
        return dict(buyer_unread=buyer_unread, producer_unread=producer_unread)

    with app.app_context():
        db.create_all()
        for sql in [
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS names_translated TEXT DEFAULT '{}'",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
            "ALTER TABLE producers ADD COLUMN IF NOT EXISTS seller_slug VARCHAR(120)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_producers_seller_slug ON producers (seller_slug)",
        ]:
            try:
                db.session.execute(text(sql))
                db.session.commit()
            except Exception:
                db.session.rollback()

        _backfill_seller_slugs()

    return app


def _backfill_seller_slugs():
    """Generate seller_slug for any producers missing one."""
    from app.models import Producer
    from app.services.slugs import unique_slug

    try:
        missing = Producer.query.filter(
            (Producer.seller_slug.is_(None)) | (Producer.seller_slug == "")
        ).all()
        if not missing:
            return
        for producer in missing:
            producer.seller_slug = unique_slug(
                producer.name,
                lambda candidate: Producer.query.filter_by(seller_slug=candidate).first() is not None,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
