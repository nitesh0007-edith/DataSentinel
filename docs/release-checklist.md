# Release Checklist

[Validation record](release-validation.md) distinguishes prior engineering checks, hosted verification and current content work.

## Code

- [x] Backend: 62/62 tests passed in engineering release
- [x] Frontend lint: TypeScript clean
- [x] Frontend production build passed
- [x] Golden path verified
- [x] Content work preserves application logic and deployment configuration

## Deployment

- [x] Backend health and heuristic RCA
- [x] Single worker / single instance with persistent runtime paths
- [x] Frontend loads and API connects
- [x] Exact-origin CORS preflight
- [x] Reset, healthy baseline and detection
- [x] Investigation cites file, line and real Git commit
- [x] Proposed repair and explicit apply approval
- [x] Validation and RESOLVED / HEALTHY
- [x] Restart persistence verified
- [x] Rollback exercised in isolated, disclosed local fixture
- [ ] Genuine hosted failed-validation/rollback capture, if that condition occurs

## Submission

- [ ] Public GitHub repository accessible to judges
- [x] Public demo URL in README and submission copy
- [x] README contains real hosted screenshots
- [x] Seven hosted screenshots with provenance
- [x] Architecture SVG and editable Mermaid source
- [x] Submission copy prepared
- [x] Seven-slide deck content prepared
- [x] 4:30 demo script prepared
- [ ] Deck exported to PDF
- [ ] Video recorded, captioned, uploaded and under five minutes
- [ ] Optional micro demo recorded
- [ ] Submission form completed
- [ ] Final repository/video/deck links verified
- [ ] Bob critic evidence attached if available
- [ ] Owner reviews and commits release content
