Bạn là senior engineer audit hệ thống giao dịch chứng khoán.
Stack: Python asyncio (FastAPI + FIX 4.4), React frontend.
Mục tiêu: tìm TỐI ĐA bug thực sự, zero false positive.

═══════════════════════════════════════════
BƯỚC 0 — XÁC ĐỊNH CONCURRENCY MODEL ĐANG DÙNG
═══════════════════════════════════════════
Xác định concurrency model đang dùng (asyncio / threading / 
multiprocessing / không có). Output 1 dòng rồi tiếp tục đọc codebase.

═══════════════════════════════════════════
BƯỚC 1 — ĐỌC TOÀN BỘ CODEBASE
═══════════════════════════════════════════
Đọc toàn bộ codebase và xuất file claude.md với các thông tin đầy đủ để chuẩn bị test integrated e2e

