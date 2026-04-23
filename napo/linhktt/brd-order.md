── DANH MỤC 1: LOGIC KHỚP LỆNH ─────────────
□ Khớp lệnh 1 phần thành công?
□ Khớp lệnh toàn bộ thành công?
□ Không khớp lệnh khi không có lệnh đối ứng thành công?
□ Thứ tự khớp lệnh đã tuân thủ đúng qui tắc ưu tiên lần lượt như sau?
 - Giá mua cao hơn > Giá mua thấp hơn.
 - Giá bán thấp hơn > Giá bán cao hơn.
 - Lệnh đặt trước > Lệnh đặt sau
 - Lệnh MARKET được ưu tiên trước lệnh LIMIT
□ Price priority: bids dùng key âm (cao → thấp)? Asks dùng key dương (thấp → cao)?
□ Market order khi book rỗng → cancelled, không khớp giá 0
□ Trade price = resting order's price (maker), không phải taker
□ filled_qty + remaining_qty == original_qty sau mỗi partial fill
□ Order state machine: fill() và cancel() có guard terminal state không?
  FILLED → không được fill/cancel thêm
  CANCELLED → không được fill/cancel thêm

── DANH MỤC 2: LOGIC ĐẶT LỆNH ─────────────
□ Đã đặt thành công lệnh LIMIT và MARKET trong phiên OPEN ?
□ Đã chặn đặt lệnh khi không trong phiên OPEN?
□ Trường Tài khoản đã validate?
  - Không được để trống, khoảng trắng
  - Không được nhập ký tự đặc biệt
□ Trường Side đã validate?
  - Không được để trống, khoảng trắng
  - Không được nhập khác MUA hoặc BÁN
□ Trường Type đã validate?
  - Không được để trống, khoảng trắng
  - Không được nhập khác LIMIT hoặc MARKET
□ Trường Khối lượng của lệnh LIMIT và MARKET đã validate đủ các yêu cầu dưới?
  - Không được để trống, khoảng trắng
  - không được nhập <= 0
  - chỉ cho nhập số nguyên dương
  - là bội của bước khối lượng đã cài đặt trên Admin
□ Trường Giá đặt lệnh LIMIT đã validate đủ các yêu cầu dưới?
  - Không được để trống, khoảng trắng
  - không được nhập <= 0
  - Giá đặt cần là số >= giá sàn và <= giá trần
  - Không được nhập chữ, ký tự đặc biệt
  - cần chia được hết cho bước giá đã cài đặt trên Admin
  - Không được nhập > 9999999999999999999
□ Mã cổ phiếu đã validate đủ các yêu cầu dưới?
  - phải nằm trong danh sách mã cổ phiếu đã khai báo trên Admin
  - Không được để trống, khoảng trắng
□ Nếu hai lệnh cùng đẩy vào hệ thống từ cùng một session → đã reject lệnh thứ 2?

── DANH MỤC 3: LOGIC Admin ─────────────
□ Cho phép Mở phiên, Đóng phiên thành công?
□ Cho phép sửa mã cổ phiếu thành công? 
□ Giá trần, Giá sàn, bước giá, bước khối lượng đã validate đủ các yêu cầu bên dưới chưa?
    - Không được để trống, khoảng trắng
    - không được nhập <= 0
    - Không được nhập số quá lớn (VD: 9999999999999999999)
    - Không được nhập chữ, ký tự đặc biệt
    - Không được nhập khác số nguyên dương
    - Giá trần - Giá sàn phải đủ lớn để chứa ít nhất 1 bước giá 
□ Thông tin bên mua, bên bán của từng mã cổ phiếu được cập nhật chính xác khi có lệnh đẩy vào, không cần load lại trang
□ Trade History cập nhật chính xác khi có lệnh đẩy vào, không cần load lại trang
□ Communication Logs lưu đầy đủ các log hệ thống khi có thay đổi, không cần load lại trang

Yêu cầu:
 - Cover:
   + Happy case
   + Negative cases
   + Edge cases
   + Boundary values