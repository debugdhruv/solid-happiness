from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

VALID_PRIORITIES = {"P1", "P2", "P3", "P4"}
VALID_STATUSES = {"Open", "In Progress", "Resolved", "Escalated", "Closed"}


@dataclass
class CleaningReport:
    rows_in: int
    rows_out: int
    duplicate_ticket_ids: int = 0
    invalid_timestamps: int = 0
    negative_resolution_times: int = 0
    invalid_priorities: int = 0
    invalid_statuses: int = 0
    missing_root_causes: int = 0
    actions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return self.__dict__


def clean_tickets(tickets: pd.DataFrame, valid_category_ids: set[int], valid_agent_ids: set[int]) -> tuple[pd.DataFrame, CleaningReport]:
    df = tickets.copy()
    report = CleaningReport(rows_in=len(df), rows_out=0)

    for col in ["created_at", "first_response_at", "resolved_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    duplicate_mask = df.duplicated(subset=["ticket_id"], keep="first")
    report.duplicate_ticket_ids = int(duplicate_mask.sum())
    if report.duplicate_ticket_ids:
        df = df.loc[~duplicate_mask].copy()
        report.actions.append("Dropped duplicate ticket_id rows, keeping first occurrence.")

    invalid_category_mask = ~df["category_id"].isin(valid_category_ids)
    if invalid_category_mask.any():
        count = int(invalid_category_mask.sum())
        df = df.loc[~invalid_category_mask].copy()
        report.actions.append(f"Dropped {count} rows with unknown category_id.")

    invalid_agent_mask = df["agent_id"].notna() & ~df["agent_id"].isin(valid_agent_ids)
    if invalid_agent_mask.any():
        count = int(invalid_agent_mask.sum())
        df = df.loc[~invalid_agent_mask].copy()
        report.actions.append(f"Dropped {count} rows with unknown agent_id.")

    invalid_timestamp_mask = df["created_at"].isna()
    report.invalid_timestamps = int(invalid_timestamp_mask.sum())
    if report.invalid_timestamps:
        df = df.loc[~invalid_timestamp_mask].copy()
        report.actions.append("Dropped rows with invalid created_at values.")

    negative_response_mask = df["first_response_at"].notna() & (df["first_response_at"] < df["created_at"])
    if negative_response_mask.any():
        df.loc[negative_response_mask, "first_response_at"] = pd.NaT
        report.actions.append("Set first_response_at to null when it preceded created_at.")

    negative_resolution_mask = df["resolved_at"].notna() & (df["resolved_at"] < df["created_at"])
    report.negative_resolution_times = int(negative_resolution_mask.sum())
    if report.negative_resolution_times:
        df.loc[negative_resolution_mask, "resolved_at"] = pd.NaT
        df.loc[negative_resolution_mask, "status"] = "In Progress"
        report.actions.append("Cleared invalid resolved_at values and reopened affected tickets.")

    invalid_priority_mask = ~df["priority"].isin(VALID_PRIORITIES)
    report.invalid_priorities = int(invalid_priority_mask.sum())
    if report.invalid_priorities:
        df = df.loc[~invalid_priority_mask].copy()
        report.actions.append("Dropped rows with invalid priorities.")

    invalid_status_mask = ~df["status"].isin(VALID_STATUSES)
    report.invalid_statuses = int(invalid_status_mask.sum())
    if report.invalid_statuses:
        df = df.loc[~invalid_status_mask].copy()
        report.actions.append("Dropped rows with invalid statuses.")

    report.missing_root_causes = int(df["root_cause"].isna().sum() + (df["root_cause"].fillna("").str.strip() == "").sum())
    df["root_cause"] = df["root_cause"].replace("", pd.NA)

    report.rows_out = len(df)
    return df, report

