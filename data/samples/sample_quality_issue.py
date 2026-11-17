# SAMPLE FILE: Contains deliberate quality issues for demo purposes
# This is SYNTHETIC code — not from any real system


def process_payment(amount, currency, customer_id, payment_method,
                    retry_count, billing_address, shipping_address):
    # TODO: add input validation
    print(f"Processing payment for {customer_id}")  # debug print

    try:
        result = charge_card(amount, currency, payment_method)
    except:
        pass  # bare except silently swallowed

    try:
        notify_customer(customer_id, amount)
    except Exception:
        pass  # exception silenced

    # FIXME: this doesn't handle partial failures
    log_transaction(customer_id, amount, currency)
    update_billing(billing_address)
    update_shipping(shipping_address)
    send_receipt(customer_id, amount)
    record_analytics(customer_id, amount, currency, payment_method)
    sync_to_erp(customer_id, amount)
    sync_to_crm(customer_id)
    trigger_fraud_check(customer_id, amount)
    archive_transaction(customer_id, amount, currency)
    notify_finance_team(amount, currency)
    update_inventory_reserve(customer_id)
    schedule_fulfillment(customer_id, shipping_address)
    generate_invoice(customer_id, amount, currency)
    send_confirmation_email(customer_id)
    update_loyalty_points(customer_id, amount)
    trigger_webhook(customer_id, "payment_complete")
    cache_invalidate(customer_id)
    refresh_dashboard(customer_id)
    post_to_audit_log(customer_id, amount, currency)
    notify_operations(amount)
    close_session(customer_id)
    finalize_payment(amount, currency)
    return True


def charge_card(amount, currency, method):
    return {"status": "ok"}


def notify_customer(cid, amount):
    pass
