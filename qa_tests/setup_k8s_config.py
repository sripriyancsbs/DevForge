import subprocess
import yaml
import tempfile
import os

def setup():
    # Read kubeconfig from WSL
    res = subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "cat", "/root/.kube/config"], capture_output=True, text=True, check=True)
    cfg = yaml.safe_load(res.stdout)

    # Update server URL to container IP on devforge network
    cfg["clusters"][0]["cluster"]["server"] = "https://172.18.0.5:6443"
    cfg["clusters"][0]["cluster"]["insecure-skip-tls-verify"] = True
    if "certificate-authority-data" in cfg["clusters"][0]["cluster"]:
        del cfg["clusters"][0]["cluster"]["certificate-authority-data"]

    temp_path = os.path.join(os.getcwd(), "kubeconfig_temp.yaml")
    with open(temp_path, "w") as f:
        yaml.dump(cfg, f)

    print(f"Written temp kubeconfig to {temp_path}")

    # Copy into WSL containers
    subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "docker", "exec", "devforge-backend", "mkdir", "-p", "/root/.kube"], check=True)
    subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "docker", "cp", "/mnt/c/Agen/DevForge/kubeconfig_temp.yaml", "devforge-backend:/root/.kube/config"], check=True)

    subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "docker", "exec", "devforge-worker", "mkdir", "-p", "/root/.kube"], check=True)
    subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "docker", "cp", "/mnt/c/Agen/DevForge/kubeconfig_temp.yaml", "devforge-worker:/root/.kube/config"], check=True)

    print("Kubeconfig successfully copied to devforge-backend and devforge-worker.")

if __name__ == "__main__":
    setup()
