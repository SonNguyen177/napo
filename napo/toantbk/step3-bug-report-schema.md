# Step 3 — Bug Report Schema

## Output rule (QUAN TRỌNG)

- Viết bằng Tiếng Việt
- GHI THẲNG vào file bằng tool `Write`, đường dẫn: `_bmad-output/planning-artifacts/bug-list-<module>.md`
<!-- - Loại trừ mọi path match pattern lấy từ .gitignore -->
- KHÔNG in bug entry ra console/chat
- Trong chat chỉ trả lời 1 dòng tổng kết: `Done. File: <path>. P0:<n>, P1:<n>, P2:<n>, P3:<n>`
- Trả về kết quả cho Main agent
- Nếu file đã tồn tại → overwrite

## Tài liệu liên quan

- `_bmad-output/data-model.md`
- `_bmad-output/module-interactions.md`

## Severity (dùng CHÍNH XÁC)

- **P0 Blocker**: app không chạy / data corruption / security breach
- **P1 Critical**: golden path flow sai/crash
- **P2 High**: edge case, validation thiếu non-critical, UI broken có workaround
- **P3 Low**: cosmetic, typo, minor

### Nguyên tắc

- Nghi ngờ giữa 2 cấp → chọn cấp CAO hơn
- Không reproducible → không report
- Không có Location exact → không report

## Schema mỗi bug (đủ các field sau)

- ID (`<SOURCE>-<MODULE>-<NNN>`)
- [ ] Fixed
- Severity
- Module, Location (`path:Lstart-Lend`)
- Description, Root cause, Impact
- Reproduction (bước cụ thể)
- Evidence (code snippet 3-10 dòng)
- Suggested fix (1-2 dòng)
- Source (`AR` | `ECH`)

## Thứ tự file

- Sort theo Severity giảm dần (P0 trên)
- Tag index ở cuối file
