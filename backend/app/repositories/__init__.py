"""Data access. The only layer that writes SQLAlchemy queries.

Services call these functions instead of building queries themselves, so the
query for "applications a recruiter may see" exists once and cannot drift
between the dashboard, the job page and the screening queue.
"""
