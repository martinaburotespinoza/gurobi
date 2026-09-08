"""Fast public-contract smoke test runnable without a Gurobi license."""
from fastapi.testclient import TestClient

from api.app import app


def main() -> None:
    client = TestClient(app)
    checks = [
        ('GET', '/health', None),
        ('GET', '/metadata', None),
        ('POST', '/solve', {
            'round_number': 1,
            'backend': 'scipy',
            'q_hot': 30,
            'q_cold': 30,
            'markup': 2.0,
            'service_rate': 1.0,
            'lambda_total': 15,
            'arrival_reference_rate': 15,
        }),
        ('POST', '/solve', {
            'round_number': 5,
            'backend': 'simulation',
            'q_hot': 30,
            'q_cold': 30,
            'markup': 2.0,
            'service_rate': 1.0,
            'lambda_total': 15,
            'arrival_reference_rate': 15,
        }),
        ('POST', '/solve', {
            'round_number': 8,
            'backend': 'simulation',
            'q_hot': 30,
            'q_cold': 30,
            'markup': 2.0,
            'service_rate': 1.0,
            'lambda_total': 15,
            'arrival_reference_rate': 15,
        }),
    ]
    for method, path, payload in checks:
        response = client.request(method, path, json=payload)
        if response.status_code != 200:
            raise SystemExit(f'FAIL {method} {path}: {response.status_code} {response.text}')
    print('PUBLIC CONTRACT: PASS')


if __name__ == '__main__':
    main()
