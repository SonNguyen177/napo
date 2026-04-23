Bạn là senior engineer audit hệ thống giao dịch chứng khoán.
Stack: Python asyncio (FastAPI + FIX 4.4), React frontend.
Mục tiêu: tìm TỐI ĐA bug thực sự, zero false positive.

═══════════════════════════════════════════
BƯỚC 2 — /bmad-qa-generate-e2e-tests để chạy test e2e
═══════════════════════════════════════════
/bmad-qa-generate-e2e-tests dựa vào file BRD @brd-context.md để thực hiện test

Yêu cầu:
 - Các testcase cần tập trung vào test tích hợp 3 hệ thống Client, Admin, Matching-engine
 - Cần hỏi lại trước khi fix bất kỳ bug nào
 - Cover:
   + Happy case
   + Negative cases
   + Edge cases
   + Boundary values

Output:
 - Sau khi chạy test xong cần xuất ra file report-bug-e2e.md gồm:
   + ID bug dạng [E2E-01] [E2E-02] [E2E-03]
   + [ ] Fixed
   + Severity: High/Medium/Low
   + Mô tả lỗi
   + Steps test để tái hiện bugkhi test manual
   + Suggested fix (1-2 dòng)
   
 - File report-bug-e2e.md cần có tổng hợp lại quá trình test đã thực hiện test bao nhiêu case, phát sinh bao nhiêu bug, các bug đã được fix hay chưa

═══════════════════════════════════════════
BƯỚC 3 — Thực hiện fix các bug được chỉ định
═══════════════════════════════════════════
Thực hiện fix tất cả các bug vừa tìm được trong @report-bug-e2e và update trạng thái Fixed
