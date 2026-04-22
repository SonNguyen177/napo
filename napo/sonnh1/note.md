# Notes.md
## Bước 1 : Chuẩn bị môi trường và cài đặt sẵn sàng :
[X] Nodejs v25 (node -v)
[X] Python 3.14
[X] Git
[X] uv 0.9.15 (uv --version)
[X] Tạo sẵn thư mục dự án, khởi tạo .git và .gitignore
[X] Tạo thư mục chung `napo` chứa knowleadge của team
[X] Tạo repo public dùng chung github : https://github.com/SonNguyen177/napo
[X] Add colabbrators vào repo github thuynt116@gmail.com , khanhtoan2511@gmail.com , kieulinh2741994@gmail.com
[X] Mở sourcetree, thiết lập remote đến github, init master và push thử
[x] Cài đặt bmad-method trên thư mục gốc `npx bmad-method install` hoặc dùng lệnh sau để cài module core và tích hợp Claude, Khi cài chọn ngôn ngữ agent sử dụng và document output và Vietnamese :
`npx bmad-method install --directory /path/to/project --modules bmm --tools claude-code --yes`
[X] Chạy `claude` hoặc `claude --dangerously-skip-permissions` trên thư mục gốc, kiểm tra đúng model reasoning Opus 4.6
[X] Kiểm tra thử các agent của bmad đã có từ terminal (generate-project-context , quick-dev, qa-generate-e2e-test , review-edge-case-hunter , document-project)

## Bước 2 : Khởi tạo context (đọc codebase)
[ ] Copy project được cho vào thư mục gốc của dự án, nếu có sẵn thư mục .git thì xoá đi
[ ] Chạy /init để claude tạo file CLAUDE.md, đọc codebase hiểu hệ thống
[ ] Sử dụng `bmad-generate-project-context` để bmad phân tích hệ thống, sinh ra file `project-context`
[ ] Thêm các rule ngoại cảnh như giới hạn cuộc thi hackathon trong 1h, thành viên 04 người và ưu tiên chính là tìm và fix bug, phát triển feature nhỏ

## Bước 3: Sinh file document hệ thống
[ ] Sử dụng lệnh `bmad-document-project` để tài liệu hoá dự án brownfield , dùng cho các bước tìm bug tiếp theo

## Bước 4 : Kiểm tra và chạy thử

## Bước 5: Phát triển tính năng mới
- Bật chế độ planning mode : (shift + tab ) x2
- Viết sẵn yêu cầu ra 1 file .md
- Chạy flow `quick-dev` để chạy qua các bước từ analysist đến review

//--------------------------------------
- Setup từ 1 folder **.git**, chỉ có file *.gitignore* và file *README.md*
- Mở thư mục trên VSCode cho dễ theo dõi file
- Copy source code, ko có các file markdown vào thư mục setup sẵn git
- Chuyển thư mục làm việc đến *cd /Users/bobby/DATA/AI/Claude_Code/Hackathon/prepare1*
- Cài đặt bmad-method bằng lệnh *npx bmad-method install* | **(+1 phút)**, chọn BMCore, Tea, CIS, Tiếng việt. Chú ý là cài bằng terminal bên ngoài, ko cài trong claude tránh lỗi

1. Khởi chạy claude code
- Chạy */claude* trên thư mục gốc
- Chọn đúng model = */model* opus 4.7
- init file CLAUDE.md = */init* | **(+1:08)**
- Kiểm tra nội dung file CLAUDE.md

2. Thực hiện đọc codebase/ build context từ bmad-method

// check nodejs version để cbi cai bmad-method
*node -v*
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
nvm install 25

Prerequisites: Node.js v20+ · Python 3.10+ · uv
*uv --version*

- Sau khi cài đặt xong mở thư mục repo bằng VSCode
- Kiểm tra các folder _bmad đã sinh ra, ví dụ _bmad-output

- Đọc codebase và tạo context cho dự án : 
 **/bmad-generate-project-context** : 22:32 -> **(+7 phút)**
Chọn C để tiếp tục các bước trong flow : sẽ có file _bmad-output/project-context.md

 Category 1: Technology Stack & Versions 
 Category 2: Language-Specific Rules.
 Category 3: Framework-Specific Rules.
 Category 4: Testing Rules.
 Category 5: Code Quality & Style Rules.
 Category 6: Development Workflow Rules.
 Category 7: Critical Don't-Miss Rules (category cuối).

Tự thêm đoạn rule sau vào file context :
### Other Rules
- Project này là để tham gia một cuộc thi AI Mini Hackathon ngắn với tổng thời gian là 01 giờ. Số lượng thành viên 04 người. Nhiệm vụ chính là phát triển tính năng mới và tìm và fix bug có sẵn
- Yêu cầu luôn bám sát rule này để đưa ra quyết định phù hợp về mặt thời gian và tài nguyên sử dụng trong cuộc thi

### Sửa file CLAUDE.md
- Sửa file CLAUDE.md , yêu cầu luôn đọc file _bmad-output/project-context.md để nắm rõ về hệ thống
và thêm đoạn config MCP Playwright

ví dụ : 
## Other rules
- Đọc file `/_bmad-output/project-context.md` cẩn thận để nắm bắt rõ ràng về hệ thống

## MCP Servers

### Playwright (browser testing)

Configured in `.mcp.json`. Uses `@playwright/mcp` to automate browser interactions for testing the Admin (:3001) and Client (:3000) UIs.

- Yêu cầu claude code "chạy file @run.sh xem hệ thống có lỗi gì không". Claude sẽ kiểm tra từng service. nếu OK sẽ bảo mình mở terminal chạy run script
- Chạy ok, commit code và push lên server

-------------------------------------
Tổng thời gian đến đây khoảng 15 phút

 Bước 2 : Phát triển tính năng mới
 - clear context, chọn planning mode
 - Chạy luồng 'bmad-quick-dev'
 - "Thêm tính năng cho phép huỷ toàn bộ lệnh đang trong queue. Chức năng huỷ tất cả lệnh chờ khớp, tất cả các mã trên hệ thống. Chức năng được dùng trên admin page" => hỏi và đáp để làm rõ yêu cầu
 - Tạo ra dc file :  "spec-cancel-all-orders.md"
 - Spec sẽ chạy qua các status sau Draft -> ready-for-dev -> in-progress -> in-review => done
 - Thực thi implement + test => mất khoảng 10 phút

Ví dụ
gọi /bmad-quick-dev (23:33 )
   Thêm tính năng vẽ chart thống kê lịch sử khớp lệnh trên web client
  - Chart cho phép view dạng nến và dạng line
  - Chart gồm các trục thời gian khoảng từ 8 đến 15h, khối lượng và giá khớp
  - Có option xem 1 mã hoặc nhiều mã trên chart
  - Yêu cầu giao diện dễ nhìn, theo style của tradingview thì càng tốt

  => mất 7 phút, đang ở bước review = 3 agents khác nhau
