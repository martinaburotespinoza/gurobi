import json

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_public_health_contract():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json().get('status') == 'ok'


def test_public_metadata_has_exactly_r1_to_r8():
    response = client.get('/metadata')
    assert response.status_code == 200
    rounds = response.json().get('rounds', [])
    assert len(rounds) == 8
    assert {int(item['round_number']) for item in rounds} == set(range(1, 9))
    assert all('R9' not in json.dumps(item, ensure_ascii=False) for item in rounds)


def _payload(round_number, backend):
    return {
        'round_number': round_number,
        'backend': backend,
        'q_hot': 30,
        'q_cold': 30,
        'markup': 2.0,
        'service_rate': 1.0,
        'lambda_total': 15,
        'arrival_reference_rate': 15,
    }


def test_public_r1_reference_executes():
    response = client.post('/solve', json=_payload(1, 'scipy'))
    assert response.status_code == 200, response.text
    assert response.json().get('round_number') == 1


def test_public_r5_simulation_executes():
    response = client.post('/solve', json=_payload(5, 'simulation'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get('round_number') == 5
    assert body.get('operational') is True


def test_public_r8_simulation_executes():
    response = client.post('/solve', json=_payload(8, 'simulation'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get('round_number') == 8
    assert body.get('operational') is True
