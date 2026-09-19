"""
Local Docker template validation suite for DevForge Phase 5.
Validates:
- Docker build for all 4 templates: Python FastAPI, React Vite, Node.js, Go Microservice
- Docker image inspect
- Container run, startup and health check response
- Clean removal of containers and images
"""

import os
import sys
import shutil
import tempfile
import subprocess
import time
import urllib.request
import json

TEMPLATES_DIR = "/mnt/c/Agen/DevForge/templates"
if not os.path.exists(TEMPLATES_DIR):
    TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

TEMPLATES_CONFIG = [
    {
        "template": "python-fastapi",
        "name": "qa-fastapi-app",
        "port": 8000,
        "host_port": 18000,
        "health_path": "/healthz",
        "replacements": {"{{PORT}}": "8000", "{{NAME}}": "qa-fastapi-app", "{{APPLICATION_NAME}}": "qa-fastapi-app", "{{VERSION}}": "1.0.0"}
    },
    {
        "template": "react-vite",
        "name": "qa-react-app",
        "port": 80,
        "host_port": 18001,
        "health_path": "/",
        "replacements": {"{{PORT}}": "80", "{{NAME}}": "qa-react-app", "{{APPLICATION_NAME}}": "qa-react-app", "{{VERSION}}": "1.0.0"}
    },
    {
        "template": "node-service",
        "name": "qa-node-app",
        "port": 3000,
        "host_port": 18002,
        "health_path": "/healthz",
        "replacements": {"{{PORT}}": "3000", "{{NAME}}": "qa-node-app", "{{APPLICATION_NAME}}": "qa-node-app", "{{VERSION}}": "1.0.0"}
    },
    {
        "template": "go-microservice",
        "name": "qa-go-app",
        "port": 8080,
        "host_port": 18003,
        "health_path": "/health",
        "replacements": {"{{PORT}}": "8080", "{{NAME}}": "qa-go-app", "{{APPLICATION_NAME}}": "qa-go-app", "{{VERSION}}": "1.0.0"}
    }
]

def render_template_to_workspace(template_name: str, dest_dir: str, replacements: dict):
    src_dir = os.path.join(TEMPLATES_DIR, template_name)
    assert os.path.exists(src_dir), f"Template dir {src_dir} does not exist"
    
    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
    
    # Process replacements in text files
    for root, _, files in os.walk(dest_dir):
        for f in files:
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                changed = False
                for k, v in replacements.items():
                    if k in content:
                        content = content.replace(k, v)
                        changed = True
                if changed:
                    with open(path, "w", encoding="utf-8") as fp:
                        fp.write(content)
            except Exception:
                pass

def test_template(cfg: dict) -> bool:
    template = cfg["template"]
    name = cfg["name"]
    host_port = cfg["host_port"]
    port = cfg["port"]
    health_path = cfg["health_path"]
    tag = f"devforge-local-test-{template}:phase5"
    container_name = f"devforge-test-run-{template}"

    print(f"\n========================================================")
    print(f"Testing Docker image build and run for template: {template}")
    print(f"========================================================")

    temp_dir = tempfile.mkdtemp(prefix=f"devforge_test_{template}_")
    try:
        render_template_to_workspace(template, temp_dir, cfg["replacements"])
        print(f"[OK] Workspace prepared at {temp_dir}")
        assert os.path.exists(os.path.join(temp_dir, "Dockerfile")), "Dockerfile missing!"

        # 1. docker build
        print(f"Building Docker image: {tag} ...")
        build_res = subprocess.run(
            ["docker", "build", "-t", tag, "."],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if build_res.returncode != 0:
            print(f"[FAIL] Docker build failed for {template}:\n{build_res.stderr}\n{build_res.stdout}")
            return False
        print(f"[OK] Docker build succeeded for {template}")

        # 2. docker image inspect
        inspect_res = subprocess.run(
            ["docker", "image", "inspect", tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        assert inspect_res.returncode == 0, f"Inspect failed: {inspect_res.stderr}"
        inspect_data = json.loads(inspect_res.stdout)
        assert len(inspect_data) > 0, "No inspect output"
        image_id = inspect_data[0].get("Id", "")
        print(f"[OK] Image inspect verified. Image ID: {image_id[:19]}...")

        # 3. docker run
        # Remove any lingering container
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"Starting container {container_name} on host port {host_port}...")
        run_res = subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "-p", f"{host_port}:{port}", tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if run_res.returncode != 0:
            print(f"[FAIL] Docker run failed: {run_res.stderr}")
            return False

        # 4. Wait for container to be healthy / reachable
        time.sleep(2)
        url = f"http://127.0.0.1:{host_port}{health_path}"
        print(f"Probing {url} ...")
        success = False
        for attempt in range(12):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "DevForge-QA"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        body = resp.read().decode("utf-8")
                        print(f"[OK] Health check passed on attempt {attempt+1}! Response ({resp.status}): {body[:80]}")
                        success = True
                        break
            except Exception as e:
                time.sleep(1)

        if not success:
            logs_res = subprocess.run(["docker", "logs", container_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"[FAIL] Container failed health check. Container logs:\n{logs_res.stdout}\n{logs_res.stderr}")
            return False

        print(f"[PASS] Template {template} successfully built and verified!")
        return True

    finally:
        # Cleanup container and image
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker", "rmi", "-f", tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"[OK] Cleaned up container {container_name}, image {tag}, and temp workspace.")

def main():
    results = {}
    for cfg in TEMPLATES_CONFIG:
        res = test_template(cfg)
        results[cfg["template"]] = res
        if not res:
            print(f"\n[FATAL] Template {cfg['template']} failed validation!")
            sys.exit(1)

    print("\n========================================================")
    print("ALL 4 TEMPLATES PASSED LOCAL DOCKER VALIDATION:")
    for tmpl, ok in results.items():
        print(f"  {tmpl:20}: {'PASS' if ok else 'FAIL'}")
    print("========================================================")

if __name__ == "__main__":
    main()
