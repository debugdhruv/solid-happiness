from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.python.data_cleaning import clean_tickets
from backend.python.db import execute_sql_file, get_engine

SEED = 1842
DEFAULT_ROWS = 15_000
END_DATE = pd.Timestamp("2026-07-31 23:59:00", tz="UTC")
START_DATE = END_DATE - pd.Timedelta(days=179)

ROOT_CAUSES = [
    "Configuration",
    "Capacity",
    "Customer Error",
    "Authentication",
    "Code Regression",
    "Vendor Outage",
    "Network Latency",
    "Certificate Expiry",
    "Data Sync",
    "Documentation Gap",
    "Permissions",
    "Monitoring Noise",
]

CATEGORY_CONFIG = [
    ("Network", "VPN", 4, 5.8, ["Configuration", "Authentication", "Network Latency", "Capacity"]),
    ("Network", "DNS", 3, 3.6, ["Configuration", "Vendor Outage", "Network Latency"]),
    ("Platform", "Compute", 6, 6.5, ["Capacity", "Configuration", "Monitoring Noise"]),
    ("Platform", "Database", 8, 9.0, ["Data Sync", "Capacity", "Code Regression"]),
    ("Application", "Login", 4, 4.2, ["Authentication", "Code Regression", "Permissions"]),
    ("Application", "Checkout", 3, 5.0, ["Code Regression", "Configuration", "Data Sync"]),
    ("Application", "API", 5, 5.5, ["Code Regression", "Permissions", "Documentation Gap"]),
    ("Security", "SSO", 4, 4.8, ["Authentication", "Certificate Expiry", "Permissions"]),
    ("Security", "Access Review", 12, 7.0, ["Permissions", "Documentation Gap", "Customer Error"]),
    ("Billing", "Invoice", 24, 10.0, ["Customer Error", "Data Sync", "Configuration"]),
    ("Billing", "Payments", 8, 8.2, ["Vendor Outage", "Data Sync", "Code Regression"]),
    ("Integrations", "Webhook", 8, 6.8, ["Customer Error", "Code Regression", "Configuration"]),
    ("Integrations", "CRM Sync", 10, 7.4, ["Data Sync", "Permissions", "Vendor Outage"]),
    ("Observability", "Alerts", 6, 3.4, ["Monitoring Noise", "Configuration", "Capacity"]),
]

AGENT_NAMES = [
    "Aarav Mehta", "Maya Chen", "Lena Ortiz", "Noah Singh", "Elena Petrova", "Owen Brooks",
    "Priya Raman", "Mateo Silva", "Grace Kim", "Ishaan Rao", "Sofia Moretti", "Daniel Park",
    "Anika Shah", "Marcus Bell", "Nina Walsh", "Rohan Iyer", "Camila Torres", "Henry Adams",
    "Fatima Khan", "Leo Martin", "Zara Ali", "Jonas Weber", "Mei Tan", "Aiden Clark",
    "Sara Nassar", "Victor Hugo", "Esha Nair", "Mila Novak", "Theo Brown", "Iris Zhou",
    "Nikhil Verma", "Amara Cole", "Julian Stone", "Leah Green", "Dev Patel", "Kiara Das",
]


def generate_agents() -> pd.DataFrame:
    teams = ["Platform", "Network", "Applications", "Billing", "Security"]
    shifts = ["Morning", "Evening", "Night"]
    levels = ["Junior", "Mid", "Senior", "Lead"]
    rows = []
    for idx, name in enumerate(AGENT_NAMES, start=1):
        rows.append({
            "agent_id": idx,
            "agent_name": name,
            "team": teams[idx % len(teams)],
            "shift": shifts[idx % len(shifts)],
            "experience_level": levels[(idx + idx // 7) % len(levels)],
            "active": idx not in {11, 29},
        })
    return pd.DataFrame(rows)


def generate_categories() -> pd.DataFrame:
    return pd.DataFrame([
        {"category_id": idx, "category_name": name, "subcategory": sub, "sla_hours": sla}
        for idx, (name, sub, sla, _mean, _causes) in enumerate(CATEGORY_CONFIG, start=1)
    ])


def weighted_created_at(rng: np.random.Generator, rows: int) -> pd.DatetimeIndex:
    days = pd.date_range(START_DATE.normalize(), END_DATE.normalize(), freq="D", tz="UTC")
    day_weights = []
    for day in days:
        week_factor = 0.62 if day.weekday() >= 5 else 1.0
        month_end_factor = 1.22 if day.day >= 26 else 1.0
        slow_drift = 1 + 0.18 * np.sin((day.dayofyear / 365) * np.pi * 3)
        incident_bump = 1.0
        if pd.Timestamp("2026-05-14", tz="UTC") <= day <= pd.Timestamp("2026-05-18", tz="UTC"):
            incident_bump = 1.85
        if pd.Timestamp("2026-07-08", tz="UTC") <= day <= pd.Timestamp("2026-07-10", tz="UTC"):
            incident_bump = 1.55
        day_weights.append(max(0.05, week_factor * month_end_factor * slow_drift * incident_bump))
    chosen_days = rng.choice(days, size=rows, p=np.array(day_weights) / np.sum(day_weights))

    hours = np.arange(24)
    hour_weights = np.array([0.55, 0.42, 0.38, 0.34, 0.32, 0.42, 0.7, 1.0, 1.35, 1.55, 1.45, 1.3, 1.2, 1.28, 1.34, 1.42, 1.55, 1.45, 1.25, 1.05, 0.88, 0.76, 0.66, 0.58])
    chosen_hours = rng.choice(hours, size=rows, p=hour_weights / hour_weights.sum())
    minutes = rng.integers(0, 60, size=rows)
    seconds = rng.integers(0, 60, size=rows)
    return pd.DatetimeIndex(chosen_days) + pd.to_timedelta(chosen_hours, unit="h") + pd.to_timedelta(minutes, unit="m") + pd.to_timedelta(seconds, unit="s")


def generate_tickets(rows: int = DEFAULT_ROWS) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    agents = generate_agents()
    categories = generate_categories()
    created_at = weighted_created_at(rng, rows)
    category_weights = np.array([1.35, 0.82, 0.9, 0.78, 1.18, 0.72, 1.1, 0.82, 0.58, 0.76, 0.62, 0.88, 0.66, 0.93])
    category_ids = rng.choice(categories["category_id"], rows, p=category_weights / category_weights.sum())
    priorities = rng.choice(["P1", "P2", "P3", "P4"], rows, p=[0.055, 0.22, 0.48, 0.245])

    rows_out = []
    duplicate_templates: list[dict[str, object]] = []
    for idx in range(rows):
        cat_id = int(category_ids[idx])
        name, subcategory, sla_hours, mean_hours, causes = CATEGORY_CONFIG[cat_id - 1]
        priority = str(priorities[idx])
        created = created_at[idx]
        hour = created.hour
        shift = "Morning" if 6 <= hour < 14 else "Evening" if 14 <= hour < 22 else "Night"
        eligible_agents = agents[(agents["shift"] == shift) & (agents["active"])]
        if rng.random() < 0.18:
            eligible_agents = agents[agents["active"]]
        agent = eligible_agents.sample(n=1, random_state=int(rng.integers(1, 1_000_000))).iloc[0]

        priority_factor = {"P1": 0.72, "P2": 0.9, "P3": 1.1, "P4": 1.28}[priority]
        night_factor = 1.18 if shift == "Night" else 1.0
        weekend_factor = 1.12 if created.weekday() >= 5 else 1.0
        base = mean_hours * priority_factor * night_factor * weekend_factor
        resolution_hours = float(rng.lognormal(mean=np.log(max(base, 0.8)), sigma=0.58))
        if rng.random() < 0.035:
            resolution_hours *= rng.uniform(2.5, 6.0)
        if name == "Network" and subcategory == "VPN" and pd.Timestamp("2026-05-14", tz="UTC") <= created <= pd.Timestamp("2026-05-18", tz="UTC"):
            resolution_hours *= rng.uniform(1.35, 2.4)
        if subcategory in {"Checkout", "Payments"} and created.day >= 26:
            resolution_hours *= rng.uniform(1.15, 1.75)

        first_response_hours = max(0.03, float(rng.gamma(shape=1.6, scale={"P1": 0.12, "P2": 0.35, "P3": 0.75, "P4": 1.2}[priority])))
        open_probability = {"P1": 0.012, "P2": 0.035, "P3": 0.055, "P4": 0.07}[priority]
        is_open = created > END_DATE - pd.Timedelta(days=10) and rng.random() < open_probability
        status = "Open" if is_open else rng.choice(["Resolved", "Closed"], p=[0.72, 0.28])
        if is_open and rng.random() < 0.46:
            status = "In Progress"

        resolved_at = pd.NaT if is_open else created + pd.Timedelta(hours=resolution_hours)
        first_response_at = created + pd.Timedelta(hours=first_response_hours)
        sla_breached = (resolved_at if pd.notna(resolved_at) else END_DATE) > created + pd.Timedelta(hours=sla_hours)
        escalation_flag = bool(rng.random() < (0.08 + (0.11 if priority in {"P1", "P2"} else 0) + (0.08 if sla_breached else 0)))
        if escalation_flag and status == "In Progress" and rng.random() < 0.35:
            status = "Escalated"

        root_cause = str(rng.choice(causes, p=np.ones(len(causes)) / len(causes)))
        if rng.random() < 0.075:
            root_cause = str(rng.choice(ROOT_CAUSES))
        if rng.random() < 0.085:
            root_cause = ""

        resolution_type = "Unresolved" if is_open else str(rng.choice(
            ["Config Change", "Code Fix", "Knowledge Base", "Vendor Fix", "Restart", "User Education", "Monitoring Update"],
            p=[0.24, 0.18, 0.13, 0.12, 0.11, 0.12, 0.10],
        ))
        if "Customer Error" == root_cause:
            resolution_type = "User Education"
        impact = str(rng.choice(["None", "Low", "Medium", "High", "Critical"], p=_impact_weights(priority)))
        description = _description(name, subcategory, priority, root_cause, rng)
        if rng.random() < 0.018 and duplicate_templates:
            original = duplicate_templates[int(rng.integers(0, len(duplicate_templates)))]
            description = str(original["description"])
            cat_id = int(original["category_id"])
            name, subcategory, sla_hours, mean_hours, causes = CATEGORY_CONFIG[cat_id - 1]
            root_cause = str(original["root_cause"])
        elif rng.random() < 0.05:
            duplicate_templates.append({"description": description, "category_id": cat_id, "root_cause": root_cause})

        rows_out.append({
            "ticket_id": f"TCK-{idx + 1:07d}",
            "category_id": cat_id,
            "agent_id": int(agent["agent_id"]),
            "priority": priority,
            "status": status,
            "created_at": created,
            "first_response_at": first_response_at,
            "resolved_at": resolved_at,
            "root_cause": root_cause,
            "resolution_type": resolution_type,
            "escalation_flag": escalation_flag,
            "customer_impact": impact,
            "description": description,
        })

    tickets = pd.DataFrame(rows_out)
    duplicate_rows = tickets.sample(frac=0.003, random_state=SEED).copy()
    tickets = pd.concat([tickets, duplicate_rows], ignore_index=True)
    bad_rows = tickets.sample(frac=0.002, random_state=SEED + 1).index
    tickets.loc[bad_rows, "resolved_at"] = tickets.loc[bad_rows, "created_at"] - pd.to_timedelta(2, unit="h")
    return agents, categories, tickets


def _impact_weights(priority: str) -> list[float]:
    if priority == "P1":
        return [0.01, 0.05, 0.2, 0.46, 0.28]
    if priority == "P2":
        return [0.03, 0.22, 0.46, 0.25, 0.04]
    if priority == "P3":
        return [0.18, 0.46, 0.27, 0.08, 0.01]
    return [0.35, 0.44, 0.17, 0.035, 0.005]


def _description(category: str, subcategory: str, priority: str, root_cause: str, rng: np.random.Generator) -> str:
    symptoms = {
        "VPN": ["users unable to establish tunnel", "MFA loop during remote login", "slow split-tunnel routing"],
        "DNS": ["intermittent name resolution", "incorrect record propagation", "service discovery timeout"],
        "Compute": ["node saturation alerts", "pod scheduling delay", "instance health check failures"],
        "Database": ["replication lag", "slow queries", "connection pool exhaustion"],
        "Login": ["failed sign-in attempts", "session timeout reports", "password reset failures"],
        "Checkout": ["payment handoff error", "cart submission timeout", "order confirmation delay"],
        "API": ["elevated 5xx rate", "token validation failures", "rate limit confusion"],
        "SSO": ["SAML assertion rejected", "certificate trust warning", "identity provider timeout"],
        "Access Review": ["access request blocked", "role mapping mismatch", "approval workflow delay"],
        "Invoice": ["invoice mismatch", "tax calculation question", "missing billing contact"],
        "Payments": ["processor decline spike", "settlement delay", "refund status mismatch"],
        "Webhook": ["delivery retry storm", "signature validation failure", "subscriber endpoint timeout"],
        "CRM Sync": ["stale customer record", "duplicate account mapping", "sync job backlog"],
        "Alerts": ["noisy monitor", "missing notification", "threshold drift"],
    }
    symptom = str(rng.choice(symptoms.get(subcategory, ["service degradation"])))
    suffix = "" if root_cause else " root cause pending RCA"
    return f"{priority} {category}/{subcategory}: {symptom}; suspected {root_cause or 'unknown'}{suffix}."


def load_database(agents: pd.DataFrame, categories: pd.DataFrame, tickets: pd.DataFrame) -> None:
    execute_sql_file(ROOT / "database" / "schema.sql")
    execute_sql_file(ROOT / "database" / "indexes.sql")
    cleaned, report = clean_tickets(tickets, set(categories["category_id"]), set(agents["agent_id"]))
    cleaned = cleaned.replace({pd.NaT: None, "": None})
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE tickets, agents, categories RESTART IDENTITY CASCADE"))
    agents.to_sql("agents", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    categories.to_sql("categories", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    cleaned.to_sql("tickets", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print("Data cleaning report:")
    for key, value in report.as_dict().items():
        print(f"  {key}: {value}")


def write_csv(output_dir: Path, agents: pd.DataFrame, categories: pd.DataFrame, tickets: pd.DataFrame) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    agents.to_csv(output_dir / "agents.csv", index=False)
    categories.to_csv(output_dir / "categories.csv", index=False)
    tickets.to_csv(output_dir / "tickets_raw.csv", index=False)
    cleaned, report = clean_tickets(tickets, set(categories["category_id"]), set(agents["agent_id"]))
    cleaned.to_csv(output_dir / "tickets_clean.csv", index=False)
    (output_dir / "cleaning_report.json").write_text(pd.Series(report.as_dict()).to_json(indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate realistic support ticket analytics data.")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="Number of primary tickets to generate before duplicate/dirty rows.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data", help="Directory for generated CSV files.")
    parser.add_argument("--skip-db", action="store_true", help="Generate CSV files without loading PostgreSQL.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    agents, categories, tickets = generate_tickets(args.rows)
    write_csv(args.output_dir, agents, categories, tickets)
    print(f"Generated {len(tickets):,} raw ticket rows into {args.output_dir}.")
    if not args.skip_db:
        load_database(agents, categories, tickets)
        print("Loaded PostgreSQL with cleaned support analytics data.")


if __name__ == "__main__":
    main()

