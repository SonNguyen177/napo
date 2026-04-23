 - /clear context, chọn planning mode (Shift + Tab) x2
 - Gọi flow 'bmad-quick-dev' thực hiện chức năng được mô tả tromng file @feature-cancel-all-order.md
 - Sau khi dev hoàn thành feature mới (check chức năng thành công), merge từ master vào nhánh feature để up-to-date thì chạy prompt `/bmad-quick-dev chạy lại các unit test đã có để verify các bug đã fix trong @planning-artifacts` để yc verify lại


Tính năng sửa lệnh
 - clear context, chọn planning mode
 - Chạy luồng 'bmad-quick-dev'
 - "Thêm tính năng cho phép huỷ toàn bộ lệnh đang trong queue. Chức năng huỷ tất cả lệnh chờ khớp, tất cả các mã trên hệ thống. Chức năng được dùng trên admin page" => hỏi và đáp để làm rõ yêu cầu
 - Tạo ra dc file :  "spec-cancel-all-orders.md"
 - Spec sẽ chạy qua các status sau Draft -> ready-for-dev -> in-progress -> in-review => done
 - Thực thi implement + test => mất khoảng 10 phút