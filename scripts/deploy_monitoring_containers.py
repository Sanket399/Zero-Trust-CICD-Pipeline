import subprocess
import os

CONTAINERS = [
    {
        "name": "prometheus",
        "image": "prom/prometheus",
        "ports": "9090:9090",
        "volume": "/home/sanket/Documents/prometheus.yml:/etc/prometheus/prometheus.yml",
        "extra_flags": "--network host",
    },
    {
        "name": "grafana",
        "image": "grafana/grafana:latest",
        "extra_flags": "--network host",
    }
]


def stop_container(name):
    """Stops and removes a Docker container if it exists."""
    print(f"Stopping and removing existing container: {name}")
    subprocess.run(f"docker rm -f {name}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_container(container):
    """Starts a Docker container based on the given configuration."""
    cmd_parts = [
        "docker run -d",
        f"--name {container['name']}",
        f"-p {container['ports']}" if "ports" in container else "",
        f"-v {container['volume']}" if "volume" in container else "",
        container.get("extra_flags", ""),
        container["image"]
    ]

    cmd = " ".join(filter(None, cmd_parts))
    print(f"Starting container: {container['name']}")

    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        print(f"{container['name']} started successfully.")
    else:
        print(f"Error starting {container['name']}:")
        print(result.stderr.decode())


def deploy_monitoring_containers():
    """Deploys Prometheus and Grafana containers."""
    for container in CONTAINERS:
        stop_container(container['name'])
        start_container(container)


if __name__ == "__main__":
    deploy_monitoring_containers()
