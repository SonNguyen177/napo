# Step 1 — Generate Project Context

Tạo mới `_bmad-output/project-context.md` TỐI GIẢN cho hackathon 1 tiếng/4 người bằng Tiếng Việt
(fix bug + thêm feature nhỏ + verify + demo E2E).

File sinh ra phải có ĐÚNG 5 section sau, tổng dưới 80 dòng. Nội dung tự discover từ code/docs/package files của project hiện tại — KHÔNG bịa:

1. **Run & Verify**
   - Lệnh install dependencies (mỗi ngôn ngữ/package manager phát hiện được)
   - Lệnh start từng service (backend, UI...) kèm port thực tế
   - 1 lệnh smoke-test đơn giản (health check, curl, hoặc tương đương)

2. **Module Map**
   - Bảng markdown: `| path | trách nhiệm | owner |`
   - 1 dòng cho mỗi module/thư mục chính của project
   - Cột owner để trống (team tự điền)

3. **Luồng chính**
   - 1 mermaid sequence diagram thể hiện luồng nghiệp vụ chính end-to-end
   - Entry point → xử lý core → output/broadcast
   - Nếu có nhiều protocol/interface song song, vẽ thêm nhánh

4. **Top Invariants (ĐỪNG PHÁ khi fix bug)**
   - 6–8 rule, mỗi rule 1 dòng
   - Chỉ những rule mà nếu phá sẽ vỡ hệ thống hoặc demo
   - Discover từ code thực tế (singleton, entry points duy nhất, protocol version
     cố định, convention data structure, đồng bộ giữa các tầng...)
   - KHÔNG đưa language syntax, code style, typing convention

5. **Demo Script**
   - Checklist 5–6 bước E2E: start stack → setup ban đầu → thao tác nghiệp vụ
     chính → verify kết quả trên UI/log → verify 1 bug đã fix (placeholder)
   - Các bước phải chạy được tuần tự, không phụ thuộc tool bên ngoài

## Ràng buộc bắt buộc

- KHÔNG sinh section về language syntax, typing, dataclass, import patterns
- KHÔNG sinh testing rules chi tiết
- KHÔNG sinh framework conventions dài (CORS, middleware, validation patterns...)
- KHÔNG time estimate
- Tiếng Việt mô tả; tên file/hàm/lệnh/port giữ tiếng Anh
- Bỏ qua ceremony "[C] Continue" — sinh thẳng file
- Cuối file 1 dòng: `"Bản rút gọn cho hackathon 1h. Chi tiết xem source + bug list."`

## Output

Ghi file, in đường dẫn, không in lại nội dung.
