from flask import Blueprint, render_template, session, abort

from app.models import Producer, Product

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/<seller_slug>")
def seller_shop(seller_slug):
    seller = Producer.query.filter_by(seller_slug=seller_slug).first()
    if not seller:
        abort(404)

    products = (
        Product.query.filter_by(producer_id=seller.id, is_active=True)
        .order_by(Product.sort_order.asc().nulls_last(), Product.created_at.desc())
        .all()
    )
    lang = session.get("language", "en")
    return render_template(
        "shop/seller_shop.html", seller=seller, products=products, lang=lang
    )
