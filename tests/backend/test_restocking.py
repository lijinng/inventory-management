"""
Tests for restocking order endpoints.
"""
import pytest


class TestRestockingOrderEndpoints:
    """Test suite for restocking orders."""

    def _forecasts(self, client):
        return {f["item_sku"]: f for f in client.get("/api/demand").json()}

    def test_demand_includes_cost_fields(self, client):
        for f in client.get("/api/demand").json():
            assert f["unit_cost"] is not None
            assert f["lead_time_days"] is not None

    def test_create_order_success(self, client):
        fc = self._forecasts(client)
        a, b = fc["WDG-001"], fc["MTR-304"]
        payload = {"items": [{"item_sku": "WDG-001", "quantity": 10},
                             {"item_sku": "MTR-304", "quantity": 2}], "budget": 10000}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["total_cost"] == pytest.approx(a["unit_cost"] * 10 + b["unit_cost"] * 2)
        assert data["lead_time_days"] == max(a["lead_time_days"], b["lead_time_days"])
        assert data["status"] == "Submitted"
        assert data["order_number"].startswith("RST-")
        assert data["estimated_delivery"]

    @pytest.mark.parametrize("items,budget", [
        ([{"item_sku": "MTR-304", "quantity": 100}], 10),
        ([], 1000),
        ([{"item_sku": "WDG-001", "quantity": 0}], 1000),
        ([{"item_sku": "WDG-001", "quantity": -5}], 1000),
        ([{"item_sku": "NOPE-000", "quantity": 1}], 1000),
    ])
    def test_create_order_invalid(self, client, items, budget):
        before = len(client.get("/api/restocking-orders").json())
        response = client.post("/api/restocking-orders", json={"items": items, "budget": budget})
        assert response.status_code == 400
        assert len(client.get("/api/restocking-orders").json()) == before

    def test_list_orders_newest_first(self, client):
        ids = []
        for qty in (1, 2):
            r = client.post("/api/restocking-orders",
                            json={"items": [{"item_sku": "WDG-001", "quantity": qty}], "budget": 1000})
            ids.append(r.json()["order_number"])
        listed = [o["order_number"] for o in client.get("/api/restocking-orders").json()]
        assert listed.index(ids[1]) < listed.index(ids[0])
