from app import db
from flask_login import UserMixin
from datetime import datetime
import json


class Producer(UserMixin, db.Model):
    def get_id(self):
        return f"p_{self.id}"


    __tablename__ = "producers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    country = db.Column(db.String(100))
    language = db.Column(db.String(10), default="en")
    bio = db.Column(db.Text)
    subscription_tier = db.Column(db.String(50), default="free")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="producer", lazy=True)
    leads = db.relationship("Lead", backref="producer", lazy=True)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey("producers.id"), nullable=False)
    name = db.Column(db.String(300), nullable=False)
    description_original = db.Column(db.Text)
    description_language = db.Column(db.String(10), default="en")
    _descriptions_translated = db.Column("descriptions_translated", db.Text, default="{}")
    _names_translated = db.Column("names_translated", db.Text, default="{}")
    marketing_text = db.Column(db.Text)
    price = db.Column(db.Float)
    currency = db.Column(db.String(10), default="EUR")
    category = db.Column(db.String(100))
    sizes_available = db.Column(db.String(500))
    _target_countries = db.Column("target_countries", db.Text, default="[]")
    _delivery_prices = db.Column("delivery_prices", db.Text, default="{}")
    _images = db.Column("images", db.Text, default="[]")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leads = db.relationship("Lead", backref="product", lazy=True)

    @property
    def descriptions_translated(self):
        return json.loads(self._descriptions_translated or "{}")

    @descriptions_translated.setter
    def descriptions_translated(self, value):
        self._descriptions_translated = json.dumps(value, ensure_ascii=False)

    @property
    def names_translated(self):
        return json.loads(self._names_translated or "{}")

    @names_translated.setter
    def names_translated(self, value):
        self._names_translated = json.dumps(value, ensure_ascii=False)

    @property
    def target_countries(self):
        return json.loads(self._target_countries or "[]")

    @target_countries.setter
    def target_countries(self, value):
        self._target_countries = json.dumps(value)

    @property
    def delivery_prices(self):
        return json.loads(self._delivery_prices or "{}")

    @delivery_prices.setter
    def delivery_prices(self, value):
        self._delivery_prices = json.dumps(value)

    @property
    def images(self):
        return json.loads(self._images or "[]")

    @images.setter
    def images(self, value):
        self._images = json.dumps(value)


class Buyer(UserMixin, db.Model):
    def get_id(self):
        return f"b_{self.id}"


    __tablename__ = "buyers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(200))
    country = db.Column(db.String(100))
    language = db.Column(db.String(10), default="en")
    _measurements = db.Column("measurements", db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leads = db.relationship("Lead", backref="buyer", lazy=True)

    @property
    def measurements(self):
        return json.loads(self._measurements or "{}")

    @measurements.setter
    def measurements(self, value):
        self._measurements = json.dumps(value)


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("buyers.id"), nullable=False)
    producer_id = db.Column(db.Integer, db.ForeignKey("producers.id"), nullable=False)
    status = db.Column(db.String(50), default="new")  # new/contacted/negotiating/confirmed/closed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship("Message", backref="lead", lazy=True)


class VerificationStatus(db.Model):
    """Per-producer per-document-type KYC verification record.

    PII rule: `masked_number` stores ONLY the last 4 digits of the ID
    (e.g. 'XXXXXX234F'). Full PAN / Aadhaar / GSTIN is never persisted.
    """

    __tablename__ = "verification_status"

    DOC_TYPES = ("pan", "gst", "aadhaar", "iec")
    STATUSES = ("pending", "verified", "failed")

    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey("producers.id"), nullable=False, index=True)
    doc_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    masked_number = db.Column(db.String(40))
    verified_name = db.Column(db.String(200))
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("producer_id", "doc_type", name="uq_verification_producer_doc"),
    )


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # buyer / producer
    sender_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    translated_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
