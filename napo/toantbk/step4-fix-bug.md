# Step 4 — Subagent: Fix Bug

## Input

Doc file `bug-list-<module>.md` — lấy bug đầu tiên từ trên xuống chưa Fixed theo `bug-id`.
Nếu không còn bug nào chưa Fixed in ra thông tin và kết thúc.

## Yêu cầu

1. Tạo branch `fix/<bug-id-lowercase>` + worktree `worktree/<bug-id-lowercase>` trong 1 lệnh.
2. Đi vào worktree này.
3. Viết unit test mô phỏng bug (phải **Fail** trên code hiện tại), đặt tại `test/unit/` (tạo folder nếu chưa có).
4. Xác nhận test fail.
5. Fix bug.
6. Chạy lại test → **Pass**.
7. Đánh dấu `[x] Fixed`, report tóm tắt thay đổi & update thông tin `Fix-summary` ngắn gọn trong `bug-list-<module>.md`.
8. Commit lên branch `fix/<bug-id-lowercase>`.
9. Đi về branch `toantbk` và đi về thư mục ban đầu.
10. In ra số lượng bug theo Severity đã fix và chưa fix
11. In ra `module: <module> - bug id: <bug-id>`

## Rules

- KHÔNG merge, KHÔNG xóa worktree
