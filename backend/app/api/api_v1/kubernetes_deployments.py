import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.kubernetes import (
    DeployApplicationRequest,
    RedeployApplicationRequest,
    KubernetesDeploymentResponse,
    KubernetesClusterStatus,
)
from app.services.kubernetes.deployment_service import deployment_service
from app.services.kubernetes.kubernetes_client import kubernetes_client
from app.services.kubernetes.exceptions import (
    KubernetesError,
    KubernetesClusterUnavailableError,
    KubernetesAuthError,
    KubernetesManifestError,
)

logger = logging.getLogger("devforge.api.kubernetes")
router = APIRouter()


@router.get("/integrations/kubernetes/status", response_model=KubernetesClusterStatus)
def get_cluster_status():
    """Check connectivity to the Kubernetes cluster and list active nodes."""
    status_dict = kubernetes_client.get_cluster_status()
    return status_dict


@router.post(
    "/applications/{application_id}/deploy",
    response_model=KubernetesDeploymentResponse,
    status_code=status.HTTP_200_OK,
)
def deploy_application(
    application_id: int,
    request: DeployApplicationRequest,
    db: Session = Depends(get_db),
):
    """
    Deploy an application to Kubernetes using its container image.
    Generates manifests, applies them idempotently, verifies rollout, and tracks status.
    """
    try:
        deployment = deployment_service.deploy(
            application_id=application_id,
            db=db,
            image_tag=request.image_tag,
            environment=request.environment or "development",
            replicas=request.replicas or 1,
            port=request.port,
        )
        status_data = deployment_service.get_deployment_status(application_id=application_id, db=db)
        if not status_data:
            raise HTTPException(status_code=404, detail="Deployment record not found after deploy")
        return status_data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except KubernetesClusterUnavailableError as ce:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ce))
    except KubernetesError as ke:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ke))
    except Exception as e:
        logger.error(f"Deployment failed for application {application_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/applications/{application_id}/deployment",
    response_model=KubernetesDeploymentResponse,
)
def get_deployment(
    application_id: int,
    db: Session = Depends(get_db),
):
    """
    Get current deployment details and real-time pod statuses for an application.
    """
    status_data = deployment_service.get_deployment_status(application_id=application_id, db=db)
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active Kubernetes deployment found for application {application_id}",
        )
    return status_data


@router.post(
    "/applications/{application_id}/deployment/redeploy",
    response_model=KubernetesDeploymentResponse,
)
def redeploy_application(
    application_id: int,
    request: RedeployApplicationRequest,
    db: Session = Depends(get_db),
):
    """
    Trigger rolling update / redeployment for an existing deployment.
    """
    try:
        deployment = deployment_service.redeploy(
            application_id=application_id,
            db=db,
            image_tag=request.image_tag,
            replicas=request.replicas,
        )
        status_data = deployment_service.get_deployment_status(application_id=application_id, db=db)
        if not status_data:
            raise HTTPException(status_code=404, detail="Deployment not found")
        return status_data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except KubernetesClusterUnavailableError as ce:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ce))
    except KubernetesError as ke:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ke))
    except Exception as e:
        logger.error(f"Redeployment failed for application {application_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/applications/{application_id}/deployment/stop",
    response_model=KubernetesDeploymentResponse,
)
def stop_application_deployment(
    application_id: int,
    db: Session = Depends(get_db),
):
    """
    Stop application workloads by scaling deployment replicas down to 0.
    """
    try:
        deployment = deployment_service.stop(application_id=application_id, db=db)
        status_data = deployment_service.get_deployment_status(application_id=application_id, db=db)
        if not status_data:
            raise HTTPException(status_code=404, detail="Deployment not found")
        return status_data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except KubernetesClusterUnavailableError as ce:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(ce))
    except KubernetesError as ke:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ke))
    except Exception as e:
        logger.error(f"Stop deployment failed for application {application_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
