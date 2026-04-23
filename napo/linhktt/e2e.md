# BƯỚC 2 — Chạy test E2E của BMAD

Dùng file `@brd-order.md` làm check list để thực hiện test thêm 1 số case logic nghiệp vụ

## Yêu cầu

- Các testcase cần tập trung vào **test tích hợp** 3 hệ thống: @matching-engine/client/ @matching-engine/exchange/admin/ @matching-engine/exchange/engine
- Cần hỏi lại trước khi fix bất kỳ bug nào.
- Cover:
  - Happy case
  - Negative cases
  - Edge cases
  - Boundary values

## Schema mỗi bug (đủ các field sau)

- ID (`E2E-<NNN>`)
- [ ] Fixed
- Severity
- Description
- Reproduction (bước cụ thể)
- Suggested fix (1-2 dòng)

## Severity (dùng CHÍNH XÁC)

- **P0 Blocker**: app không chạy / data corruption / security breach/ Happy case
- **P1 Critical**: golden path flow sai/crash
- **P2 High**: edge case, Negative cases, Boundary values, validation thiếu non-critical, UI broken có workaround
- **P3 Low**: cosmetic, typo, minor

## Output rule (QUAN TRỌNG)

- Viết bằng Tiếng Việt.
- GHI THẲNG vào file bằng tool `Write`, đường dẫn: `_bmad-output/planning-artifacts/report-bug-e2e.md`.
- File output cần có phần tổng hợp lại quá trình test:
  - Đã thực hiện test bao nhiêu case
  - Phát sinh bao nhiêu bug
  - Các bug đã được fix hay chưa
