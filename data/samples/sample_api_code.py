# SAMPLE FILE: FastAPI route code — triggers API standards check
# This is SYNTHETIC code — not from any real system

from fastapi import FastAPI

app = FastAPI()


@app.get("/orders")
def list_orders():
    return {"orders": []}


@app.post("/Orders")          # uppercase in path — standards violation
def create_order(order: dict):
    # No auth check on write endpoint
    return {"id": "new-id", "status": "created"}


@app.delete("/orders/{order_id}")
def cancel_order(order_id: str):
    # No auth dependency — missing authentication
    return {"cancelled": True}


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    return {"id": order_id, "status": "shipped"}
