# Step 2 — Document Project

## Input

Đọc `project-context.md` đã có ở `output_folder`.

## Output

Produce 4 files, mỗi file <200 dòng. Nội dung phản ánh ĐÚNG thực tế project:
chỉ viết điều code thực sự cho thấy, không suy diễn, không thêm thành phần không tồn tại.

### 1. `architecture.md`

- Mô tả component thực tế tìm thấy (BE / Admin / FE / + bất cứ thứ gì khác).
- Nếu có DB → mô tả. Nếu không → skip.
- Nếu có external service / queue / cache / file storage → mô tả.
  Nếu không → skip, không bịa.
- Mermaid diagram CHỈ nếu giúp agent hiểu boundary nhanh hơn prose;
  không bắt buộc.
- Mỗi component: responsibility 2-3 dòng + path gốc.

### 2. `data-model.md`

- Nếu project có persistence (DB / ORM / file-based store) → list
  entity/schema chính + quan hệ. Mermaid `erDiagram` nếu >2 entity có quan hệ.
- Nếu project stateless / không có data model → ghi rõ `"no persistence layer"`
  và list data structure trung tâm thay thế (type, interface, state shape
  của FE/Admin nếu đáng kể).
- Không tự thêm entity chỉ vì "thường có".

### 3. `flows.md`

- Liệt kê flow chính code thực sự implement (auth nếu có, business flow
  chính, admin flow nếu khác biệt).
- Mỗi flow: bước thực thi theo code path, chú thích endpoint / function thực tế.
- Sequence diagram Mermaid nếu flow có >3 module tương tác; ngược lại dùng
  bullet tuần tự.
- Không tạo flow giả định chưa có code.

### 4. `module-interactions.md`

- Table: `caller → callee → method/endpoint/function → purpose`.
- Bao gồm: BE↔FE, BE↔Admin, Admin↔FE (nếu có), BE↔external (nếu có),
  module nội bộ gọi nhau nếu coupling đáng kể.
- Highlight integration point dễ lỗi (auth check, validation boundary,
  state sync, cross-module assumption).

## Rules

- Viết bằng Tiếng Việt
- Bỏ qua deployment, infra, CI/CD, scaling, ADR, contribution guide.
- Mermaid dùng khi HỮU ÍCH cho LLM parse structure, không dùng để "cho đẹp".
- Không viết prose giới thiệu dài. Bullet + code reference là đủ.
- Không tạo file khác ngoài 4 file trên.
- Không hỏi lại trừ blocker thật sự.
