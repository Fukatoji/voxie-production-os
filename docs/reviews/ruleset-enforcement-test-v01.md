# Production OS ruleset enforcement test v01

Purpose: verify the active `Production OS main protection` ruleset without changing production, canon, provider, media, spend, or publication state.

This pull request must not be merged. It exists only to confirm that:

- Production OS CI is required;
- one non-author approval is required;
- stale approvals are dismissed after new pushes;
- the most recent reviewable push requires approval;
- unresolved conversations block merge;
- force pushes and branch deletion are blocked by the ruleset.

After verification, close the test pull request without merge.
