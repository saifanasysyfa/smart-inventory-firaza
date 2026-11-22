from fastapi.testclient import TestClient
from src import db
import api


def test_stock_transactions_update_stock_and_reject_negative(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()
    db.add_material('T001', 'Test Material', 'Packaging', 'pcs', 10, 3, 2, 'Test Supplier')
    material = db.get_materials()[0]
    db.record_transaction(material['material_id'], 'STOCK_IN', 5, 'test receipt')
    assert float(db.get_materials()[0]['current_stock']) == 15
    db.record_transaction(material['material_id'], 'STOCK_OUT', 4, 'test usage')
    assert float(db.get_materials()[0]['current_stock']) == 11
    db.record_transaction(material['material_id'], 'STOCK_OPNAME', 9, 'physical count')
    assert float(db.get_materials()[0]['current_stock']) == 9
    try:
        db.record_transaction(material['material_id'], 'STOCK_OUT', 10, 'invalid')
        assert False, 'Expected stock-out validation to fail'
    except ValueError:
        pass


def test_api_health_and_prediction():
    client = TestClient(api.app)
    assert client.get('/health').status_code == 200
    response = client.post('/predict', json={
        'current_stock': 5, 'minimum_stock': 10, 'usage_7d': 4,
        'usage_30d': 20, 'lead_time_days': 5
    })
    assert response.status_code == 200
    assert response.json()['status'] in {'Safe', 'Need Attention', 'Restock Priority'}
