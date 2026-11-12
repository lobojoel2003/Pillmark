# Security policy

## Supported versions

Security fixes go into the latest release. Docker images are tagged per version and
rebuilt for each release.

## Reporting a vulnerability

Please report vulnerabilities privately with
[GitHub's private vulnerability reporting](https://github.com/lobojoel2003/Pillmark/security/advisories/new)
rather than in a public issue. Include steps to reproduce and the version (`/v1/meta`
on the API, or the footer of the site).

You should get a reply within a week. Once a fix is released, the advisory will credit
you unless you ask otherwise.

## Scope notes

- The API is read-only and public by design; it has no accounts or secrets.
- The importer parses XML from DailyMed with external entities, DTDs and network access
  disabled.
- Pillmark is not a medical device. Wrong or missing pill data from manufacturer labels
  is a data issue, not a security issue, but please still report it.
