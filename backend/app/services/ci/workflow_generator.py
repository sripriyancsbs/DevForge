import yaml
from typing import Dict, Any, Optional
from app.services.ci.exceptions import CIWorkflowGenerationError


class WorkflowGenerator:
    """
    Generates real executable GitHub Actions CI workflows (.github/workflows/ci.yml)
    tailored to each application starter template with automated GHCR image publishing.
    """

    SUPPORTED_TEMPLATES = {
        "python-fastapi", "react-vite", "go-microservice", "node-service",
        "node-express", "go-gin"
    }

    def generate_workflow(
        self,
        app_name: str,
        runtime: str = "python",
        template: str = "python-fastapi",
        port: int = 8000,
        **kwargs
    ) -> str:
        """Alias for generate_workflow_yaml for backward and cross-service compatibility."""
        return self.generate_workflow_yaml(template_id=template, app_name=app_name, port=port)

    def generate_workflow_yaml(
        self,
        template_id: str,
        app_name: str,
        port: int = 8000
    ) -> str:
        """
        Generate workflow YAML string for the specified template.
        """
        template_clean = (template_id or "").strip().lower()
        if template_clean not in self.SUPPORTED_TEMPLATES:
            raise CIWorkflowGenerationError(
                f"Unsupported template '{template_id}' for CI workflow generation. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_TEMPLATES))}"
            )

        if template_clean == "python-fastapi":
            return self._generate_python_fastapi_workflow(app_name)
        elif template_clean == "react-vite":
            return self._generate_react_vite_workflow(app_name)
        elif template_clean in {"node-service", "node-express"}:
            return self._generate_node_service_workflow(app_name)
        elif template_clean in {"go-microservice", "go-gin"}:
            return self._generate_go_microservice_workflow(app_name)
        else:
            raise CIWorkflowGenerationError(f"Unhandled template: {template_id}")

    def _generate_docker_steps(self, app_name: str) -> str:
        return f"""    - name: Log in to GitHub Container Registry
      run: |
        echo "${{{{ secrets.GITHUB_TOKEN }}}}" | docker login ghcr.io -u "${{{{ github.actor }}}}" --password-stdin

    - name: Build, Tag & Publish Docker Image to GHCR
      run: |
        IMAGE_NAME="ghcr.io/${{{{ github.repository_owner }}}}/{app_name}"
        IMAGE_NAME=$(echo "$IMAGE_NAME" | tr '[:upper:]' '[:lower:]')
        COMMIT_SHA="${{{{ github.sha }}}}"
        SHORT_SHA=$(echo "$COMMIT_SHA" | cut -c1-7)

        echo "Building image: $IMAGE_NAME with tags: latest, sha-$SHORT_SHA, $COMMIT_SHA"
        docker build \\
          -t "$IMAGE_NAME:latest" \\
          -t "$IMAGE_NAME:sha-$SHORT_SHA" \\
          -t "$IMAGE_NAME:$COMMIT_SHA" \\
          .

        echo "Publishing container images to GHCR..."
        docker push "$IMAGE_NAME:latest"
        docker push "$IMAGE_NAME:sha-$SHORT_SHA"
        docker push "$IMAGE_NAME:$COMMIT_SHA"

        IMAGE_DIGEST=$(docker inspect --format='{{{{index .RepoDigests 0}}}}' "$IMAGE_NAME:latest" || echo "")
        echo "Successfully published image to GHCR: $IMAGE_NAME:sha-$SHORT_SHA"
        echo "Image Digest: $IMAGE_DIGEST"
"""

    def _generate_python_fastapi_workflow(self, app_name: str) -> str:
        docker_steps = self._generate_docker_steps(app_name)
        return f"""name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  packages: write

jobs:
  build-and-test:
    name: Build, Test & Publish to GHCR
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
        cache: 'pip'
        cache-dependency-path: requirements.txt

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest httpx

    - name: Validate syntax & imports
      run: |
        python -m py_compile main.py

    - name: Run unit tests
      run: |
        PYTHONPATH=. pytest -v

{docker_steps}"""

    def _generate_react_vite_workflow(self, app_name: str) -> str:
        docker_steps = self._generate_docker_steps(app_name)
        return f"""name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  packages: write

jobs:
  build-and-test:
    name: Build, Test & Publish to GHCR
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Node.js 20
      uses: actions/setup-node@v4
      with:
        node-version: 20

    - name: Install dependencies
      run: npm install

    - name: Build production bundle
      run: npm run build

{docker_steps}"""

    def _generate_node_service_workflow(self, app_name: str) -> str:
        docker_steps = self._generate_docker_steps(app_name)
        return f"""name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  packages: write

jobs:
  build-and-test:
    name: Build, Test & Publish to GHCR
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Node.js 20
      uses: actions/setup-node@v4
      with:
        node-version: 20

    - name: Install dependencies
      run: npm install

    - name: Run unit tests
      run: npm test

{docker_steps}"""

    def _generate_go_microservice_workflow(self, app_name: str) -> str:
        docker_steps = self._generate_docker_steps(app_name)
        return f"""name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  packages: write

jobs:
  build-and-test:
    name: Build, Test & Publish to GHCR
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Go 1.22
      uses: actions/setup-go@v5
      with:
        go-version: '1.22'

    - name: Download dependencies
      run: go mod tidy

    - name: Check code formatting
      run: |
        if [ -n "$(gofmt -l .)" ]; then
          echo "Go code is not formatted according to gofmt:"
          gofmt -d .
          exit 1
        fi

    - name: Run unit tests
      run: go test -v ./...

    - name: Build binary
      run: go build -v -o server .

{docker_steps}"""


workflow_generator = WorkflowGenerator()
