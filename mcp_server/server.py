"""
MCP Server — CRA Expenses Connector
Exposes two tools to Claude: submit_expenses and get_status.
Run with: python server.py or uv run server.py
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

# Allow imports from the mcp_server directory
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import FastMCP

from schemas import ConfirmedSubmission, SubmissionReport
from submit_expenses_core import run_submission
from get_status_core import get_status as _get_status, StatusReport

# Configure logging so all modules (submit_expenses_core, get_status_core) share the same format
logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

# Create the FastMCP server instance.
# The instructions tell Claude how and when to use the tools.
mcp = FastMCP(
    name="cra-expenses-connector",
    instructions=(
        "You help consultants submit their expense reports and CRA to Portalite. "
        "IMPORTANT: always show a summary to the consultant and wait for explicit confirmation "
        "BEFORE calling submit_expenses. Never submit without human validation."
    ),
)


# MCP tool: submit_expenses
# Called after the consultant explicitly confirms the submission.
# Forwards the validated ConfirmedSubmission payload to the core submission logic.
@mcp.tool()
async def submit_expenses(
    submission: ConfirmedSubmission,
    email: str,
    password: str,
) -> SubmissionReport:
    """
    Submit confirmed expense reports and/or CRA to Portalite.

    Only call this tool AFTER explicit confirmation from the consultant.

    Parameters
    ----------
    submission  : validated payload (expenses + CRA events + month submission)
    email       : consultant Portalite email
    password    : consultant Portalite password

    Returns
    -------
    SubmissionReport with :
    - summary    : human-readable summary (show this to the consultant)
    - expenses   : result per expense (created id or error)
    - cra_events : result per CRA event
    - cra_month  : result of the month submission
    """
    return await run_submission(submission, email, password)


# MCP tool: get_status
# Called when the consultant asks "what is the status of my submissions?".
# Queries Portalite and returns status for expenses and CRA months.
@mcp.tool()
async def get_status(
    email: str,
    password: str,
    month: Optional[str] = None,
) -> StatusReport:
    """
    Get the status of recent submissions on Portalite.

    Parameters
    ----------
    email    : consultant Portalite email
    password : consultant Portalite password
    month    : optional filter, format YYYY-MM (e.g. '2026-05')

    Returns
    -------
    StatusReport with :
    - summary    : human-readable summary (show this to the consultant)
    - expenses   : list of expenses with status (Pending/Validated/Rejected)
    - cra_months : list of CRA months with status
    """
    return await _get_status(email, password, month)


# Entry point when running the server directly
if __name__ == "__main__":
    mcp.run()