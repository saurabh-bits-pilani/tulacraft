from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Product, Message, Lead
from app.services import gemma, translation

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health():
    return {"status": "ok"}


@api_bp.route("/translate-one", methods=["POST"])
@login_required
def translate_one():
    data = request.get_json()
    product_id = data.get("product_id")
    lang = data.get("lang")
    source_lang = data.get("source_lang", "en")
    description = data.get("description", "")
    name = data.get("name", "")
    if not product_id or not lang or not description:
        return jsonify({"error": "missing fields"}), 400
    product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first_or_404()
    try:
        desc_translated = translation.translate_one(description, lang, source_lang)
        name_translated = translation.translate_one(name, lang, source_lang) if name else name
        translations = dict(product.descriptions_translated or {})
        translations[lang] = desc_translated
        product.descriptions_translated = translations
        names = dict(product.names_translated or {})
        names[lang] = name_translated
        product.names_translated = names
        db.session.commit()
        return jsonify({"lang": lang, "description": desc_translated, "name": name_translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/translate-message", methods=["POST"])
def translate_message():
    from flask import session
    data = request.get_json()
    message_id = data.get("message_id")
    target_lang = data.get("target_lang", "en")
    if not message_id:
        return jsonify({"error": "missing message_id"}), 400
    msg = Message.query.get_or_404(message_id)
    lead = Lead.query.get(msg.lead_id)
    buyer_id = session.get("buyer_id")
    producer_authenticated = current_user.is_authenticated and hasattr(current_user, "products")
    if not (buyer_id == lead.buyer_id or (producer_authenticated and current_user.id == lead.producer_id)):
        return jsonify({"error": "unauthorized"}), 403
    source_lang = data.get("source_lang", "en")
    try:
        translated = translation.translate_one(msg.content, target_lang, source_lang, max_tokens=512)
        msg.translated_content = translated
        db.session.commit()
        return jsonify({"translated": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/gemma/translate", methods=["POST"])
def translate():
    data = request.get_json()
    text = data.get("text", "")
    languages = data.get("languages", ["en"])
    source = data.get("source_language", "en")
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        return jsonify(translation.translate(text, languages, source))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/gemma/generate", methods=["POST"])
def generate():
    data = request.get_json()
    description = data.get("description", "")
    language = data.get("language", "en")
    if not description:
        return jsonify({"error": "description is required"}), 400
    try:
        return jsonify({"marketing_text": gemma.generate_marketing_text(description, language)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/gemma/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        return jsonify({"transcription": gemma.transcribe_voice(text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
