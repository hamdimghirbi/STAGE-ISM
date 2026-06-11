"""
Serveur MCP — CRA Expenses Connector
run with python server.py or uv run server.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import FastMCP

from schemas import ConfirmedSubmission, SubmissionReport
from submit_expenses_core import run_submission

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

mcp = FastMCP(
    name="cra-expenses-connector",
    instructions=(
        "You help consultants submit their expense reports and CRA to Portalite. "
        "IMPORTANT: always show a summary to the consultant and wait for explicit confirmation "
        "BEFORE calling submit_expenses. Never submit without human validation."
    ),
)


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


if __name__ == "__main__":
    mcp.run()