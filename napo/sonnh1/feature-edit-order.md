# Tính năng sửa lệnh

## Mô tả tính năng :
 *Yêu cầu* : 
- Thêm tính năng cho phép sửa lệnh đang trong order book
 *Phạm vi* :
 - Chỉ sửa các lệnh KHÔNG ở trạng thái ĐÃ KHỚP , ĐÃ HUỶ
 - Chỉ cho phép sửa KHỐI LƯỢNG và GIÁ, KHÔNG sửa side
 - Lệnh được sửa không còn ưu tiên thời gian

 *Hệ thống* :
 - Dùng trên admin page
 - Dùng trên client page

 *Giao diện* :
 - Có nút "Sửa" trên mỗi lệnh trong danh sách lệnh
 - Khi ấn nút "Sửa" thì bật dialog mới, được phép sửa giá và khối lượng
 - Khi ấn nút "Lưu" thì sẽ cập nhật thông tin lệnh lên hệ thống, engine broadcast trạng thái lệnh, sắp xếp sổ lệnh cho các client, admin page

