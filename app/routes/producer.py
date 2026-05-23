from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import db
from app.models import Producer, Product, Lead, Message
from app.services import gemma, translation
import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

def _upload_to_cloudinary(file, product_id, index):
    result = cloudinary.uploader.upload(
        file,
        folder=f"craftbridge/{product_id}",
        public_id=f"photo_{index}",
        overwrite=True,
    )
    return result["secure_url"]

producer_bp = Blueprint("producer", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@producer_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        country = request.form.get("country", "")
        language = request.form.get("language", "en")
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("producer/register.html")

        if Producer.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return render_template("producer/register.html")

        producer = Producer(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            country=country,
            language=language,
        )
        db.session.add(producer)
        db.session.commit()
        login_user(producer)
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("producer.dashboard"))

    return render_template("producer/register.html")


@producer_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        producer = Producer.query.filter_by(email=email).first()
        if producer and check_password_hash(producer.password_hash, password):
            login_user(producer)
            return redirect(url_for("producer.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("producer/login.html")


@producer_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("producer.login"))


@producer_bp.route("/dashboard")
@login_required
def dashboard():
    leads = Lead.query.filter_by(producer_id=current_user.id).order_by(Lead.created_at.desc()).all()
    products_count = Product.query.filter_by(producer_id=current_user.id).count()
    return render_template("producer/dashboard.html", leads=leads, products_count=products_count)


@producer_bp.route("/products")
@login_required
def products():
    prods = Product.query.filter_by(producer_id=current_user.id).all()
    return render_template("producer/products.html", products=prods)


@producer_bp.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", 0)
        currency = request.form.get("currency", "EUR")
        category = request.form.get("category", "")
        sizes = request.form.get("sizes", "")
        target_countries = request.form.getlist("target_countries")

        product = Product(
            producer_id=current_user.id,
            name=name,
            description_original=description,
            description_language=current_user.language,
            price=float(price) if price else 0,
            currency=currency,
            category=category,
            sizes_available=sizes,
        )
        product.target_countries = target_countries
        db.session.add(product)
        db.session.commit()

        files = request.files.getlist("photos")
        if files and files[0].filename:
            primary_index = int(request.form.get("primary_photo", 0))
            images = []
            for file in files:
                if file and allowed_file(file.filename):
                    url = _upload_to_cloudinary(file, product.id, len(images))
                    images.append(url)
            if images and primary_index < len(images):
                images.insert(0, images.pop(primary_index))
            if images:
                product.images = images
                db.session.commit()

        flash("Product saved.", "success")
        if request.form.get("do_translate") == "1" and description and target_countries:
            return redirect(url_for("producer.product_edit", product_id=product.id, translate="1"))
        return redirect(url_for("producer.products"))

    return render_template("producer/product_form.html")


@producer_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id):
    product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first_or_404()
    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.description_original = request.form.get("description", "").strip()
        product.price = float(request.form.get("price", 0) or 0)
        product.currency = request.form.get("currency", "EUR")
        product.category = request.form.get("category", "")
        product.sizes_available = request.form.get("sizes", "")
        product.sort_order = int(request.form.get("sort_order", 0) or 0)
        target_countries = request.form.getlist("target_countries")
        product.target_countries = target_countries

        db.session.commit()
        flash("Product saved.", "success")

        files = request.files.getlist("photos")
        if files and files[0].filename:
            primary_index = int(request.form.get("primary_photo", 0))
            images = []
            for file in files:
                if file and allowed_file(file.filename):
                    url = _upload_to_cloudinary(file, product_id, len(images))
                    images.append(url)
            if images and primary_index < len(images):
                images.insert(0, images.pop(primary_index))
            if images:
                product.images = images
                db.session.commit()

        return redirect(url_for("producer.products"))

    return render_template("producer/product_edit.html", product=product)


@producer_bp.route("/products/<int:product_id>/upload", methods=["POST"])
@login_required
def product_upload(product_id):
    product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first_or_404()
    files = request.files.getlist("photos")

    upload_folder = os.path.join(current_app.root_path, "static", "uploads", str(current_user.id))
    os.makedirs(upload_folder, exist_ok=True)

    images = product.images
    for file in files:
        if file and allowed_file(file.filename):
            url = _upload_to_cloudinary(file, product_id, len(images))
            images.append(url)

    product.images = images
    db.session.commit()
    flash("Photos uploaded successfully.", "success")
    return redirect(url_for("producer.products"))


@producer_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def product_delete(product_id):
    product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first_or_404()
    upload_folder = os.path.join(current_app.root_path, "static", "uploads", str(current_user.id))
    for img_path in (product.images or []):
        full_path = os.path.join(current_app.root_path, img_path.lstrip("/"))
        if os.path.exists(full_path):
            os.remove(full_path)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("producer.products"))


@producer_bp.route("/generate-marketing", methods=["POST"])
@login_required
def generate_marketing():
    data = request.get_json()
    description = (data.get("description") or "").strip()
    languages = data.get("languages") or []
    tone = data.get("tone", "elegant")

    if not description:
        return jsonify({"error": "No description provided"}), 400

    try:
        target_langs = languages if languages else [current_user.language]
        results = gemma.generate_marketing_multilang(description, target_langs, tone, current_user.language)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@producer_bp.route("/generate-marketing-source", methods=["POST"])
@login_required
def generate_marketing_source():
    data = request.get_json()
    description = (data.get("description") or "").strip()
    tone = data.get("tone", "elegant")
    if not description:
        return jsonify({"error": "No description provided"}), 400
    try:
        source_text = gemma._generate_marketing_source(description, tone, current_user.language)
        return jsonify({"source_text": source_text, "language": current_user.language})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@producer_bp.route("/translate-marketing-one", methods=["POST"])
@login_required
def translate_marketing_one():
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", "en")
    if not text or not lang:
        return jsonify({"error": "missing fields"}), 400
    try:
        translated = translation.translate_one(text, lang, current_user.language)
        return jsonify({"lang": lang, "text": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@producer_bp.route("/messages/<int:lead_id>", methods=["GET", "POST"])
@login_required
def messages(lead_id):
    lead = Lead.query.filter_by(id=lead_id, producer_id=current_user.id).first_or_404()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            db.session.add(Message(
                lead_id=lead_id,
                sender_type="producer",
                sender_id=current_user.id,
                content=content,
            ))
            lead.status = "contacted"
            db.session.commit()
    msgs = Message.query.filter_by(lead_id=lead_id).order_by(Message.created_at).all()
    from datetime import datetime
    for msg in msgs:
        if msg.sender_type == "buyer" and msg.read_at is None:
            msg.read_at = datetime.utcnow()
    db.session.commit()
    return render_template("producer/messages.html", lead=lead, messages=msgs)
