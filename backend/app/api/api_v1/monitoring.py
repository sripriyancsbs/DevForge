from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_monitoring_metrics():
    return {
        "global": {
            "p50_latency_ms": 18.4,
            "p95_latency_ms": 42.1,
            "p99_latency_ms": 112.5,
            "avg_error_rate": "0.02%",
            "total_throughput_rps": 4410,
            "slo_status": "99.98% (Met Target)"
        },
        "service_metrics": [
            {
                "service": "payment-gateway",
                "rps": 420,
                "p95_latency": "38 ms",
                "error_rate": "0.00%",
                "cpu": "14.2%",
                "memory": "340 MB",
                "status": "healthy"
            },
            {
                "service": "auth-service",
                "rps": 890,
                "p95_latency": "14 ms",
                "error_rate": "0.01%",
                "cpu": "8.5%",
                "memory": "128 MB",
                "status": "healthy"
            },
            {
                "service": "inventory-api",
                "rps": 310,
                "p95_latency": "285 ms",
                "error_rate": "1.42%",
                "cpu": "82.4%",
                "memory": "1420 MB",
                "status": "warning"
            },
            {
                "service": "customer-dashboard",
                "rps": 640,
                "p95_latency": "22 ms",
                "error_rate": "0.00%",
                "cpu": "4.1%",
                "memory": "85 MB",
                "status": "healthy"
            },
            {
                "service": "event-stream-ingestor",
                "rps": 2150,
                "p95_latency": "18 ms",
                "error_rate": "0.02%",
                "cpu": "26.8%",
                "memory": "780 MB",
                "status": "healthy"
            }
        ]
    }
