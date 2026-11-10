
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from database.db import db
from database.models import (
    PurchaseRequest, RequestLine, Supplier, RFQ, RFQSupplier,
    SupplierQuote, SupplierQuoteLine, PurchaseOrder,
    PurchaseOrderLine, Delivery, AuditEvent
)

def next_id(model, prefix, width=6):
    numbers = []
    for row in model.query.all():
        value = str(row.id)
        if value.startswith(prefix):
            try:
                numbers.append(int(value.rsplit("-", 1)[-1]))
            except ValueError:
                pass
    return f"{prefix}{max(numbers, default=0) + 1:0{width}d}"

def audit(entity_type, entity_id, event, old_value=None, new_value=None,
          reason="", actor="Procurement Admin"):
    db.session.add(AuditEvent(
        entity_type=entity_type, entity_id=str(entity_id),
        event_type=event, old_value=old_value, new_value=new_value,
        reason=reason, actor=actor, occurred_at=datetime.now()
    ))

def register_remaining_routes(app):

    # ---------------- RFQ creation ----------------
    @app.route("/rfqs/create/<request_id>", methods=["POST"])
    def create_rfq(request_id):
        pr = db.session.get(PurchaseRequest, request_id)
        if not pr:
            flash("Purchase request not found.", "error")
            return redirect(url_for("rfqs"))
        if pr.status != "APPROVED":
            flash("Only approved requests can be converted into RFQs.", "error")
            return redirect(url_for("rfqs"))
        if RFQ.query.filter_by(request_id=pr.id).first():
            flash("An RFQ already exists for this request.", "error")
            return redirect(url_for("rfqs"))

        suppliers = (Supplier.query.filter_by(is_active=True)
                     .order_by(Supplier.risk_score.asc(), Supplier.id.asc())
                     .limit(3).all())
        if len(suppliers) < 3:
            flash("At least three active suppliers are required.", "error")
            return redirect(url_for("rfqs"))

        try:
            rfq_id = next_id(RFQ, "RFQ-2026-")
            rfq = RFQ(
                id=rfq_id, request_id=pr.id,
                created_date=date.today(),
                closing_date=date.today() + timedelta(days=7),
                status="OPEN", competitive=True,
                exception_reason=None
            )
            db.session.add(rfq)
            db.session.flush()

            for supplier in suppliers:
                db.session.add(RFQSupplier(
                    rfq_id=rfq.id, supplier_id=supplier.id,
                    invited_at=datetime.now(), response_status="INVITED"
                ))

            old_status = pr.status
            pr.status = "RFQ_CREATED"
            audit("RFQ", rfq_id, "RFQ_CREATED", None, "OPEN",
                  "RFQ created and three active suppliers invited")
            audit("PurchaseRequest", pr.id, "REQUEST_CONVERTED_TO_RFQ",
                  old_status, pr.status, "RFQ created")
            db.session.commit()
            flash(f"RFQ {rfq_id} created. Three suppliers invited.", "success")
        except Exception as exc:
            db.session.rollback()
            flash(f"RFQ creation failed: {exc}", "error")
        return redirect(url_for("rfqs"))

    # ---------------- Quote submission page ----------------
    @app.route("/rfqs/<rfq_id>/quote", methods=["GET", "POST"])
    def submit_supplier_quote(rfq_id):
        rfq = db.session.get(RFQ, rfq_id)
        if not rfq:
            flash("RFQ not found.", "error")
            return redirect(url_for("quotes"))

        pr = db.session.get(PurchaseRequest, rfq.request_id)
        invitations = RFQSupplier.query.filter_by(rfq_id=rfq.id).all()
        invited_ids = [x.supplier_id for x in invitations]
        suppliers = Supplier.query.filter(
            Supplier.id.in_(invited_ids), Supplier.is_active == True
        ).all() if invited_ids else []

        if request.method == "POST":
            try:
                supplier = db.session.get(Supplier, request.form.get("supplier_id"))
                total = Decimal(request.form.get("total_landed_cost", "0"))
                delivery_days = int(request.form.get("delivery_days", "0"))
                valid_until = date.fromisoformat(request.form.get("valid_until", ""))

                invitation = RFQSupplier.query.filter_by(
                    rfq_id=rfq.id, supplier_id=supplier.id if supplier else None
                ).first()

                if not supplier or not invitation:
                    raise ValueError("Select a supplier invited to this RFQ.")
                if not supplier.is_active:
                    raise ValueError("This supplier is inactive.")
                if rfq.status != "OPEN" or date.today() > rfq.closing_date:
                    raise ValueError("This RFQ is closed.")
                if total <= 0 or delivery_days <= 0:
                    raise ValueError("Enter a positive quote amount and delivery time.")
                if valid_until <= rfq.closing_date:
                    raise ValueError("Quote validity must extend beyond the RFQ closing date.")

                lines = RequestLine.query.filter_by(request_id=pr.id).all()
                if not lines:
                    raise ValueError("The request has no line items.")

                existing_numbers = []
                for q in SupplierQuote.query.all():
                    try:
                        existing_numbers.append(int(q.id.rsplit("-", 1)[-1]))
                    except (ValueError, AttributeError):
                        pass
                quote_number = max(existing_numbers, default=0) + 1
                quote_id = f"QUO-{supplier.supplier_code}-2026-{quote_number:06d}"

                estimated_total = sum(
                    (Decimal(str(line.estimated_total)) for line in lines),
                    Decimal("0")
                )
                if estimated_total <= 0:
                    raise ValueError("Request line total must be positive.")

                ratio = total / estimated_total
                subtotal = total
                quote = SupplierQuote(
                    id=quote_id, rfq_id=rfq.id, supplier_id=supplier.id,
                    quote_date=date.today(), valid_until=valid_until,
                    currency=pr.currency, subtotal=subtotal,
                    tax_amount=Decimal("0"), shipping_cost=Decimal("0"),
                    other_cost=Decimal("0"), total_landed_cost=total,
                    delivery_days=delivery_days, status="RECEIVED",
                    is_awarded=False
                )
                db.session.add(quote)
                db.session.flush()

                existing_line_numbers = []
                for ql in SupplierQuoteLine.query.all():
                    try:
                        existing_line_numbers.append(int(ql.id.rsplit("-", 1)[-1]))
                    except (ValueError, AttributeError):
                        pass
                line_number = max(existing_line_numbers, default=0) + 1

                for line in lines:
                    line_total = (
                        Decimal(str(line.estimated_total)) * ratio
                    ).quantize(Decimal("0.01"))
                    unit_price = (
                        line_total / Decimal(str(line.quantity))
                    ).quantize(Decimal("0.01"))
                    db.session.add(SupplierQuoteLine(
                        id=f"QTL-2026-{line_number:07d}",
                        quote_id=quote.id, request_line_id=line.id,
                        quantity=line.quantity, unit_price=unit_price,
                        line_total=line_total
                    ))
                    line_number += 1

                invitation.response_status = "QUOTED"
                audit("SupplierQuote", quote_id, "QUOTE_SUBMITTED",
                      None, "RECEIVED",
                      f"Supplier {supplier.name} submitted quotation")
                db.session.commit()
                flash(f"Quotation {quote_id} submitted successfully.", "success")
                return redirect(url_for("quotes"))

            except (ValueError, InvalidOperation, TypeError) as exc:
                db.session.rollback()
                flash(str(exc), "error")
            except IntegrityError:
                db.session.rollback()
                flash("A duplicate quotation or line ID was detected. Please retry.", "error")
            except Exception as exc:
                db.session.rollback()
                flash(f"Quote submission failed: {exc}", "error")

        return render_template(
            "submit_quote.html", rfq=rfq, pr=pr, suppliers=suppliers
        )

    # ---------------- Supplier award and PO ----------------
    @app.route("/quotes/<quote_id>/award", methods=["POST"])
    def award_supplier_quote(quote_id):
        quote = db.session.get(SupplierQuote, quote_id)
        if not quote:
            flash("Quotation not found.", "error")
            return redirect(url_for("quotes"))

        rfq = db.session.get(RFQ, quote.rfq_id)
        pr = db.session.get(PurchaseRequest, rfq.request_id) if rfq else None
        supplier = db.session.get(Supplier, quote.supplier_id) if quote else None

        try:
            if not rfq or not pr or not supplier:
                raise ValueError("RFQ, request or supplier record is missing.")
            if quote.is_awarded or quote.status == "AWARDED":
                raise ValueError("This quotation has already been awarded.")
            if rfq.status != "OPEN":
                raise ValueError("This RFQ is no longer open.")
            if pr.status not in ("RFQ_CREATED", "APPROVED"):
                raise ValueError("The purchase request is not eligible for award.")
            if not supplier.is_active:
                raise ValueError("Cannot award an inactive supplier.")
            if quote.currency != pr.currency:
                raise ValueError("Currency mismatch: quotation and request currencies differ.")
            if quote.quote_date > rfq.closing_date:
                raise ValueError("Quotation was submitted after RFQ closing.")
            if quote.valid_until <= rfq.closing_date:
                raise ValueError("Quotation is expired at the RFQ closing date.")
            if quote.status not in ("RECEIVED", "SUBMITTED"):
                raise ValueError("Quotation is not in a receivable status.")

            rationale = request.form.get(
                "award_rationale", "Selected after price, delivery and supplier eligibility review."
            ).strip()

            # Ensure this quote is the lowest eligible quote.
            candidates = SupplierQuote.query.filter_by(
                rfq_id=rfq.id
            ).all()
            eligible = []
            for candidate in candidates:
                candidate_supplier = db.session.get(Supplier, candidate.supplier_id)
                if (candidate_supplier and candidate_supplier.is_active
                    and candidate.currency == pr.currency
                    and candidate.quote_date <= rfq.closing_date
                    and candidate.valid_until > rfq.closing_date
                    and candidate.status in ("RECEIVED", "SUBMITTED")
                    and not candidate.is_awarded):
                    eligible.append(candidate)

            if not eligible:
                raise ValueError("No eligible quotations are available.")
            best = min(eligible, key=lambda q: (
                Decimal(str(q.total_landed_cost)),
                q.delivery_days, candidate_supplier.risk_score if False else q.id
            ))
            if best.id != quote.id:
                raise ValueError(
                    f"Supplier award blocked. Lowest eligible quotation is {best.id}. "
                    "Select the lowest eligible quote."
                )

            po_id = next_id(PurchaseOrder, "PO-2026-")
            po = PurchaseOrder(
                id=po_id, request_id=pr.id, quote_id=quote.id,
                supplier_id=supplier.id, po_date=date.today(),
                currency=quote.currency, subtotal=quote.subtotal,
                tax_amount=quote.tax_amount, shipping_cost=quote.shipping_cost,
                total_amount=quote.total_landed_cost, status="ISSUED",
                award_rationale=rationale, issued_without_approval=False
            )
            db.session.add(po)
            db.session.flush()

            quote_lines = SupplierQuoteLine.query.filter_by(
                quote_id=quote.id
            ).all()
            if not quote_lines:
                raise ValueError("Quotation has no line items; PO cannot be created.")

            existing_po_line_numbers = []
            for item in PurchaseOrderLine.query.all():
                try:
                    existing_po_line_numbers.append(int(item.id.rsplit("-", 1)[-1]))
                except (ValueError, AttributeError):
                    pass
            po_line_number = max(existing_po_line_numbers, default=0) + 1
            total_quantity = 0

            for qline in quote_lines:
                request_line = db.session.get(RequestLine, qline.request_line_id)
                if not request_line:
                    raise ValueError("A quotation line refers to a missing request line.")
                total_quantity += int(qline.quantity)
                db.session.add(PurchaseOrderLine(
                    id=f"POL-2026-{po_line_number:07d}",
                    po_id=po.id, quote_line_id=qline.id,
                    item_name=request_line.item_name,
                    quantity=qline.quantity, unit_price=qline.unit_price,
                    line_total=qline.line_total
                ))
                po_line_number += 1

            quote.is_awarded = True
            quote.status = "AWARDED"
            rfq.status = "AWARDED"
            pr.status = "ORDERED"

            delivery_id = next_id(Delivery, "DEL-2026-")
            db.session.add(Delivery(
                id=delivery_id, po_id=po.id,
                delivery_date=date.today(),
                expected_date=date.today() + timedelta(days=quote.delivery_days),
                item_quantity=total_quantity, received_quantity=0,
                status="PENDING", notes="Delivery created automatically after PO award"
            ))

            audit("SupplierQuote", quote.id, "SUPPLIER_AWARDED",
                  "RECEIVED", "AWARDED", rationale)
            audit("PurchaseOrder", po.id, "PURCHASE_ORDER_CREATED",
                  None, "ISSUED", f"Created from awarded quote {quote.id}")
            audit("Delivery", delivery_id, "DELIVERY_CREATED",
                  None, "PENDING", "Delivery record created with purchase order")
            audit("PurchaseRequest", pr.id, "REQUEST_ORDERED",
                  "RFQ_CREATED", "ORDERED", f"Purchase order {po.id} issued")
            db.session.commit()
            flash(f"Supplier awarded. PO {po_id} and delivery {delivery_id} created.", "success")

        except (ValueError, InvalidOperation, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
        except IntegrityError:
            db.session.rollback()
            flash("A duplicate PO or PO line ID was detected. No award was saved.", "error")
        except Exception as exc:
            db.session.rollback()
            flash(f"Supplier award failed: {exc}", "error")

        return redirect(url_for("quotes"))

    # ---------------- Delivery updates ----------------
    @app.route("/deliveries/<delivery_id>/update", methods=["POST"])
    def update_delivery(delivery_id):
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            flash("Delivery record not found.", "error")
            return redirect(url_for("deliveries"))

        try:
            received = int(request.form.get("received_quantity", "-1"))
            notes = request.form.get("notes", "").strip()
            ordered = int(delivery.item_quantity)

            if received < 0 or received > ordered:
                raise ValueError(f"Received quantity must be between 0 and {ordered}.")

            old_status = delivery.status
            delivery.received_quantity = received
            delivery.notes = notes or delivery.notes

            if received == 0:
                delivery.status = "PENDING"
            elif received < ordered:
                delivery.status = "PARTIAL"
            else:
                delivery.status = "DELIVERED"

            po = db.session.get(PurchaseOrder, delivery.po_id)
            pr = db.session.get(PurchaseRequest, po.request_id) if po else None

            if po:
                if delivery.status == "DELIVERED":
                    po.status = "DELIVERED"
                elif delivery.status == "PARTIAL":
                    po.status = "PARTIALLY_DELIVERED"
                else:
                    po.status = "ISSUED"

            if pr:
                if delivery.status == "DELIVERED":
                    pr.status = "COMPLETED"
                elif delivery.status == "PARTIAL":
                    pr.status = "PARTIALLY_DELIVERED"
                else:
                    pr.status = "ORDERED"

            audit("Delivery", delivery.id, "DELIVERY_UPDATED",
                  old_status, delivery.status,
                  f"Received {received} of {ordered} units. {notes}")
            db.session.commit()
            flash(f"Delivery {delivery.id} updated: {delivery.status}.", "success")

        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
        except Exception as exc:
            db.session.rollback()
            flash(f"Delivery update failed: {exc}", "error")

        return redirect(url_for("deliveries"))
