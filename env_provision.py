#!/usr/bin/env python3
"""
env_provision.py
----------------
Reads env.toml and provisions three categories of environment variables:

  1. config  → Vault KV  +  Kubernetes ConfigMap  (non-sensitive)
  2. secrets → Vault KV only; ESO syncs them into a K8s Secret
  3. dynamic → Configures Vault database secrets engine + role
               (Vault generates actual credentials at runtime — nothing
                sensitive is written by this script)

Requirements:
    pip install hvac tomllib-backport pyyaml

Usage:
    # Set these before running (or export them in your shell profile):
    #   VAULT_ADDR   e.g. http://127.0.0.1:8200
    #   VAULT_TOKEN  your root / provisioning token

    python env_provision.py                         # provisions all services
    python env_provision.py --service my-api        # provisions one service
    python env_provision.py --dry-run               # prints what would happen
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
from typing import Any

import hvac
import yaml

# ---------------------------------------------------------------------------
# Python 3.11+ ships tomllib in stdlib; older versions need tomli.
# ---------------------------------------------------------------------------
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib          # pip install tomli
    except ModuleNotFoundError:
        sys.exit(
            "ERROR: tomllib not available.\n"
            "  Python < 3.11: pip install tomli\n"
            "  Python >= 3.11: tomllib is built-in (check your interpreter version)"
        )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BOLD  = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED   = "\033[31m"
RESET = "\033[0m"

def log(msg: str, level: str = "info") -> None:
    colours = {"info": GREEN, "warn": YELLOW, "error": RED}
    prefix   = {"info": "✓", "warn": "⚠", "error": "✗"}
    colour   = colours.get(level, "")
    print(f"{colour}{prefix.get(level, '·')} {msg}{RESET}")


def run_kubectl(manifest_yaml: str, dry_run: bool, description: str) -> None:
    """Apply a YAML manifest string via kubectl."""
    if dry_run:
        print(f"\n{YELLOW}[DRY RUN] Would kubectl apply: {description}{RESET}")
        print(textwrap.indent(manifest_yaml.strip(), "    "))
        return

    result = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=manifest_yaml.encode(),
        capture_output=True,
    )
    if result.returncode == 0:
        log(f"kubectl applied: {description}")
    else:
        log(f"kubectl failed for {description}:\n{result.stderr.decode()}", "error")
        sys.exit(1)


def ensure_namespace(namespace: str, dry_run: bool) -> None:
    """Create the namespace if it doesn't already exist."""
    manifest = yaml.dump({
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": namespace},
    })
    run_kubectl(manifest, dry_run, f"Namespace/{namespace}")


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------

def vault_client() -> hvac.Client:
    addr  = os.environ.get("VAULT_ADDR",  "http://127.0.0.1:8200")
    token = os.environ.get("VAULT_TOKEN", "")
    if not token:
        sys.exit(
            "ERROR: VAULT_TOKEN environment variable is not set.\n"
            "  export VAULT_TOKEN=<your-token>  (PowerShell: $env:VAULT_TOKEN = '...')"
        )
    client = hvac.Client(url=addr, token=token)
    if not client.is_authenticated():
        sys.exit(f"ERROR: Could not authenticate with Vault at {addr}. Check VAULT_TOKEN.")
    return client


def ensure_kv_engine(client: hvac.Client, mount: str = "secret") -> None:
    """Enable KV-v2 at `mount` if not already present."""
    try:
        mounts = client.sys.list_mounted_secrets_engines()["data"]
        if f"{mount}/" not in mounts:
            client.sys.enable_secrets_engine("kv", path=mount, options={"version": "2"})
            log(f"Enabled KV-v2 engine at path '{mount}'")
    except Exception as exc:
        log(f"Could not verify/create KV engine: {exc}", "warn")


def vault_kv_write(
    client: hvac.Client,
    path: str,
    data: dict[str, Any],
    mount: str,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"\n{YELLOW}[DRY RUN] Would write to Vault KV {mount}/{path}:{RESET}")
        for k, v in data.items():
            masked = v if len(str(v)) <= 4 else str(v)[:2] + "***"
            print(f"    {k} = {masked}")
        return

    client.secrets.kv.v2.create_or_update_secret(
        path=path, secret=data, mount_point=mount
    )
    log(f"Vault KV write → {mount}/{path}  ({len(data)} key(s))")


# ---------------------------------------------------------------------------
# Scenario 1 — Config: Vault KV + ConfigMap
# ---------------------------------------------------------------------------

def provision_config(
    client: hvac.Client,
    service: str,
    config: dict[str, str],
    namespace: str,
    kv_mount: str,
    dry_run: bool,
) -> None:
    if not config:
        return

    print(f"\n{BOLD}[{service}] config{RESET}")

    # 1a. Write to Vault KV so there is a single source of truth
    vault_kv_write(client, f"{service}/config", config, kv_mount, dry_run)

    # 1b. Apply a Kubernetes ConfigMap so pods can consume without Vault dependency
    manifest = yaml.dump({
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": f"{service}-config",
            "namespace": namespace,
            "labels": {"managed-by": "env-provision"},
        },
        "data": {k: str(v) for k, v in config.items()},
    })
    run_kubectl(manifest, dry_run, f"ConfigMap/{service}-config")


# ---------------------------------------------------------------------------
# Scenario 2 — Secrets: Vault KV only (ESO syncs to K8s Secret)
# ---------------------------------------------------------------------------

def provision_secrets(
    client: hvac.Client,
    service: str,
    secrets: dict[str, str],
    namespace: str,
    kv_mount: str,
    dry_run: bool,
) -> None:
    if not secrets:
        return

    print(f"\n{BOLD}[{service}] secrets{RESET}")

    # Write to Vault — ESO ExternalSecret will sync this into a K8s Secret
    vault_kv_write(client, f"{service}/secrets", secrets, kv_mount, dry_run)

    # Apply an ExternalSecret so ESO knows to sync this path
    external_secret = yaml.dump({
        "apiVersion": "external-secrets.io/v1",
        "kind": "ExternalSecret",
        "metadata": {
            "name": f"{service}-secrets",
            "namespace": namespace,
            "labels": {"managed-by": "env-provision"},
        },
        "spec": {
            "refreshInterval": "1m",
            "secretStoreRef": {
                "name": "vault-backend",        # your ClusterSecretStore name
                "kind": "ClusterSecretStore",
            },
            "target": {
                "name": f"{service}-secrets",   # the K8s Secret ESO will create
                "creationPolicy": "Owner",
                "deletionPolicy": "Delete",
            },
            "dataFrom": [{
                "extract": {
                    "key": f"{service}/secrets",
                    # conversionStrategy maps Vault keys → K8s Secret keys as-is
                    "conversionStrategy": "Default",
                },
            }],
        },
    })
    run_kubectl(external_secret, dry_run, f"ExternalSecret/{service}-secrets")


# ---------------------------------------------------------------------------
# Scenario 3 — Dynamic: Configure Vault database engine + role
# ---------------------------------------------------------------------------

def provision_dynamic(
    client: hvac.Client,
    service: str,
    dynamic_cfg: dict,
    dry_run: bool,
) -> None:
    databases = dynamic_cfg.get("databases", [])
    if not databases:
        return

    print(f"\n{BOLD}[{service}] dynamic secrets{RESET}")

    for db in databases:
        name           = db["name"]
        plugin         = db["plugin"]
        connection_url = db["connection_url"]
        admin_user     = db["vault_admin_user"]
        admin_pass     = db["vault_admin_pass"]
        role_name      = db["role_name"]
        default_ttl    = db.get("default_ttl", "1h")
        max_ttl        = db.get("max_ttl", "24h")
        creation_sql   = db["creation_sql"]

        if dry_run:
            print(f"\n{YELLOW}[DRY RUN] Would configure Vault database engine:{RESET}")
            print(f"    Connection: {name}  plugin={plugin}")
            print(f"    Role:       {role_name}  ttl={default_ttl}/{max_ttl}")
            print(f"    SQL:        {creation_sql.strip()[:80]}...")
            continue

        # Enable database secrets engine if not already present
        try:
            mounts = client.sys.list_mounted_secrets_engines()["data"]
            if "database/" not in mounts:
                client.sys.enable_secrets_engine("database")
                log("Enabled database secrets engine")
        except Exception as exc:
            log(f"Could not verify database engine: {exc}", "warn")

        # Configure the database connection
        try:
            client.secrets.database.configure(
                name=name,
                plugin_name=plugin,
                connection_url=connection_url,
                allowed_roles=[role_name],
                username=admin_user,
                password=admin_pass,
            )
            log(f"Vault DB connection configured: {name}")
        except Exception as exc:
            log(f"Failed to configure DB connection '{name}': {exc}", "error")
            continue

        # Create the role that defines what SQL Vault runs to generate creds
        try:
            client.secrets.database.create_role(
                name=role_name,
                db_name=name,
                creation_statements=[creation_sql],
                default_ttl=default_ttl,
                max_ttl=max_ttl,
            )
            log(f"Vault DB role configured: {role_name}  (ttl={default_ttl}, max={max_ttl})")
        except Exception as exc:
            log(f"Failed to create role '{role_name}': {exc}", "error")

        log(
            f"Dynamic creds available at:  vault read database/creds/{role_name}",
            "info",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision env vars to Vault + Kubernetes")
    parser.add_argument(
        "--config", default="env.toml", help="Path to env.toml (default: env.toml)"
    )
    parser.add_argument(
        "--service", default=None, help="Provision a single service only"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would happen without making changes"
    )
    parser.add_argument(
        "--kv-mount", default="secret", help="Vault KV mount path (default: secret)"
    )
    args = parser.parse_args()

    # ── Load config ──────────────────────────────────────────────────────────
    if not os.path.exists(args.config):
        sys.exit(f"ERROR: Config file not found: {args.config}")

    cfg       = load_toml(args.config)
    namespace = cfg.get("namespace")
    services  = cfg.get("services", {})

    if not namespace:
        sys.exit("ERROR: 'namespace' key is missing from the top of env.toml")
    if not services:
        sys.exit("ERROR: No [services.*] sections found in env.toml")

    if args.service and args.service not in services:
        sys.exit(
            f"ERROR: Service '{args.service}' not found in env.toml.\n"
            f"  Available: {', '.join(services.keys())}"
        )

    target_services = (
        {args.service: services[args.service]} if args.service else services
    )

    print(f"\n{BOLD}env_provision.py{RESET}")
    print(f"  Config file : {args.config}")
    print(f"  Namespace   : {namespace}")
    print(f"  Services    : {', '.join(target_services.keys())}")
    print(f"  KV mount    : {args.kv_mount}")
    print(f"  Dry run     : {args.dry_run}")
    print()

    # ── Connect to Vault ─────────────────────────────────────────────────────
    client = vault_client()
    log(f"Connected to Vault at {os.environ.get('VAULT_ADDR', 'http://127.0.0.1:8200')}")
    ensure_kv_engine(client, args.kv_mount)

    # ── Ensure namespace exists ──────────────────────────────────────────────
    ensure_namespace(namespace, args.dry_run)

    # ── Provision each service ───────────────────────────────────────────────
    for service_name, service_cfg in target_services.items():
        print(f"\n{'─' * 60}")
        print(f"{BOLD}Service: {service_name}{RESET}")

        provision_config(
            client=client,
            service=service_name,
            config=service_cfg.get("config", {}),
            namespace=namespace,
            kv_mount=args.kv_mount,
            dry_run=args.dry_run,
        )
        provision_secrets(
            client=client,
            service=service_name,
            secrets=service_cfg.get("secrets", {}),
            namespace=namespace,
            kv_mount=args.kv_mount,
            dry_run=args.dry_run,
        )
        provision_dynamic(
            client=client,
            service=service_name,
            dynamic_cfg=service_cfg.get("dynamic", {}),
            dry_run=args.dry_run,
        )

    print(f"\n{'─' * 60}")
    log("Done.")


if __name__ == "__main__":
    main()
