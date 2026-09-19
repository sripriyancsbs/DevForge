import os
import requests
import dotenv

dotenv.load_dotenv()
token = os.getenv("GITHUB_TOKEN")
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "DevForge-QA"
}

repo = "sripriyancsbs/qa-ci-py-56014"
run_id = "35380286257"

r = requests.get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs", headers=headers).json()
for job in r.get("jobs", []):
    print(f"Job: {job['name']} -> {job['conclusion']}")
    for s in job.get("steps", []):
        print(f"  Step: {s['name']} -> {s['conclusion']}")
    
    log_res = requests.get(f"https://api.github.com/repos/{repo}/actions/jobs/{job['id']}/logs", headers=headers)
    print("\n--- Failed Step Details ---")
    lines = log_res.text.splitlines()
    for l in lines:
        if any(w in l for w in ["FAILED", "ERROR", "error", "Traceback", "pytest", "docker"]):
            print(l)
