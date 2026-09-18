from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_infrastructure_status():
    return {
        "summary": {
            "total_nodes": 18,
            "healthy_nodes": 18,
            "managed_databases": 6,
            "redis_caches": 4,
            "network_gateways": 3,
            "monthly_estimate": "$4,280 / mo"
        },
        "clusters": [
            {
                "name": "prod-useast1-primary",
                "region": "us-east-1",
                "provider": "AWS EKS",
                "version": "v1.29.3",
                "nodes": 8,
                "cpu_utilization": "54%",
                "memory_utilization": "68%",
                "status": "healthy"
            },
            {
                "name": "stage-useast2-secondary",
                "region": "us-east-2",
                "provider": "AWS EKS",
                "version": "v1.29.3",
                "nodes": 4,
                "cpu_utilization": "32%",
                "memory_utilization": "45%",
                "status": "healthy"
            },
            {
                "name": "dev-uswest2-sandbox",
                "region": "us-west-2",
                "provider": "AWS EKS",
                "version": "v1.28.7",
                "nodes": 4,
                "cpu_utilization": "22%",
                "memory_utilization": "30%",
                "status": "healthy"
            },
            {
                "name": "preview-eucentral1",
                "region": "eu-central-1",
                "provider": "AWS EKS",
                "version": "v1.29.3",
                "nodes": 2,
                "cpu_utilization": "15%",
                "memory_utilization": "20%",
                "status": "healthy"
            }
        ],
        "datastores": [
            {
                "name": "postgres-primary-prod",
                "engine": "PostgreSQL 16.2",
                "allocated_storage": "500 GB (34% used)",
                "connections": "48 / 200",
                "status": "healthy"
            },
            {
                "name": "redis-cluster-session",
                "engine": "Redis 7.2",
                "allocated_storage": "16 GB (62% used)",
                "connections": "180 / 1000",
                "status": "healthy"
            },
            {
                "name": "clickhouse-analytics",
                "engine": "ClickHouse 24.1",
                "allocated_storage": "2 TB (45% used)",
                "connections": "12 / 100",
                "status": "healthy"
            }
        ]
    }
