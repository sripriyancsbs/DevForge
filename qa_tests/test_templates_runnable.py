import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.provisioning.project_generator import project_generator


def to_wsl_path(win_path: Path) -> str:
    """Convert a Windows Path to a WSL mount path /mnt/c/..."""
    p = win_path.resolve()
    drive = p.drive[0].lower()
    path_part = p.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{path_part}"


def test_fastapi_template():
    print("\n==========================================")
    print("Testing Python FastAPI Template")
    print("==========================================")
    temp_dir = Path("c:/Agen/DevForge/.devforge/test_runnable_fastapi").resolve()
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        res = project_generator.generate_project(
            template_id="python-fastapi",
            target_dir=temp_dir,
            application_name="runnable-fastapi-app",
            port=8000,
            environment="production",
            database_type="postgresql"
        )
        assert res.app_name == "runnable-fastapi-app"
        print("[OK] Generated python-fastapi project successfully")

        val = project_generator.validate_generated_project(
            project_dir=temp_dir,
            application_name="runnable-fastapi-app",
            template_id="python-fastapi"
        )
        assert val["valid"] is True
        print("[OK] Validated generated python-fastapi project structure")

        # Run unit tests
        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp_dir)
        test_run = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_main.py", "-v"],
            cwd=str(temp_dir),
            env=env,
            capture_output=True,
            text=True
        )
        print("Test Output:\n", test_run.stdout)
        if test_run.returncode != 0:
            print("Test Err:\n", test_run.stderr)
        assert test_run.returncode == 0, "Python FastAPI tests failed"
        print("[OK] Python FastAPI unit tests passed")

        # Build Docker container via WSL
        wsl_path = to_wsl_path(temp_dir)
        docker_cmd = ["wsl", "-u", "root", "docker", "build", "-t", "devforge-qa-fastapi:latest", wsl_path]
        print(f"Building Docker image: {' '.join(docker_cmd)}")
        d_run = subprocess.run(docker_cmd, capture_output=True, text=True)
        if d_run.returncode != 0:
            print("Docker Build Err:\n", d_run.stderr)
        assert d_run.returncode == 0, f"Docker build failed for python-fastapi: {d_run.stderr}"
        print("[OK] Docker container build succeeded for python-fastapi")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_node_template():
    print("\n==========================================")
    print("Testing Node.js Express Template")
    print("==========================================")
    temp_dir = Path("c:/Agen/DevForge/.devforge/test_runnable_node").resolve()
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        res = project_generator.generate_project(
            template_id="node-express",
            target_dir=temp_dir,
            application_name="runnable-node-app",
            port=3000,
            environment="production"
        )
        assert res.app_name == "runnable-node-app"
        print("[OK] Generated node-express project successfully")

        val = project_generator.validate_generated_project(
            project_dir=temp_dir,
            application_name="runnable-node-app",
            template_id="node-express"
        )
        assert val["valid"] is True
        print("[OK] Validated generated node-express project structure")

        # Install express dependency & run tests
        npm_cmd = ["npm.cmd" if sys.platform == "win32" else "npm", "install", "--no-audit", "--no-fund"]
        print("Running npm install...")
        install_run = subprocess.run(npm_cmd, cwd=str(temp_dir), capture_output=True, text=True)
        assert install_run.returncode == 0, f"npm install failed: {install_run.stderr}"
        print("[OK] npm install succeeded")

        node_cmd = ["node", "test.js"]
        test_run = subprocess.run(node_cmd, cwd=str(temp_dir), capture_output=True, text=True)
        print("Test Output:\n", test_run.stdout)
        assert test_run.returncode == 0, f"Node tests failed: {test_run.stderr}"
        print("[OK] Node.js Express unit tests passed")

        # Build Docker container via WSL
        wsl_path = to_wsl_path(temp_dir)
        docker_cmd = ["wsl", "-u", "root", "docker", "build", "-t", "devforge-qa-node:latest", wsl_path]
        print(f"Building Docker image: {' '.join(docker_cmd)}")
        d_run = subprocess.run(docker_cmd, capture_output=True, text=True)
        if d_run.returncode != 0:
            print("Docker Build Err:\n", d_run.stderr)
        assert d_run.returncode == 0, f"Docker build failed for node-express: {d_run.stderr}"
        print("[OK] Docker container build succeeded for node-express")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_go_template():
    print("\n==========================================")
    print("Testing Go Gin Template")
    print("==========================================")
    temp_dir = Path("c:/Agen/DevForge/.devforge/test_runnable_go").resolve()
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        res = project_generator.generate_project(
            template_id="go-gin",
            target_dir=temp_dir,
            application_name="runnablegoapp",
            port=8080,
            environment="production"
        )
        assert res.app_name == "runnablegoapp"
        print("[OK] Generated go-gin project successfully")

        val = project_generator.validate_generated_project(
            project_dir=temp_dir,
            application_name="runnablegoapp",
            template_id="go-gin"
        )
        assert val["valid"] is True
        print("[OK] Validated generated go-gin project structure")

        # Run go test on Windows
        print("Running go test ./...")
        go_tidy = subprocess.run(["go", "mod", "tidy"], cwd=str(temp_dir), capture_output=True, text=True)
        print("go mod tidy output:\n", go_tidy.stdout, go_tidy.stderr)
        test_run = subprocess.run(["go", "test", "-v", "./..."], cwd=str(temp_dir), capture_output=True, text=True)
        print("Go Test Output:\n", test_run.stdout)
        assert test_run.returncode == 0, f"Go tests failed: {test_run.stderr}"
        print("[OK] Go Gin unit tests passed")

        # Build Docker container via WSL
        wsl_path = to_wsl_path(temp_dir)
        docker_cmd = ["wsl", "-u", "root", "docker", "build", "-t", "devforge-qa-go:latest", wsl_path]
        print(f"Building Docker image: {' '.join(docker_cmd)}")
        d_run = subprocess.run(docker_cmd, capture_output=True, text=True)
        if d_run.returncode != 0:
            print("Docker Build Err:\n", d_run.stderr)
        assert d_run.returncode == 0, f"Docker build failed for go-gin: {d_run.stderr}"
        print("[OK] Docker container build succeeded for go-gin")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_fastapi_template()
    test_node_template()
    test_go_template()
    print("\n=======================================================")
    print("ALL 3 INITIAL TEMPLATES VERIFIED RUNNABLE & CONTAINERIZABLE!")
    print("=======================================================")
