# TikTok Affiliate Studio – Đặc tả MVP tiết kiệm

**Phiên bản** 1.1
**Trạng thái** Đề xuất triển khai

## Mục tiêu

Đăng thử 5 video Affiliate trên một kênh TikTok, gắn đúng sản phẩm và đo thời gian làm mỗi video. Dùng một mẫu M07 Photo Slideshow để kiểm chứng toàn bộ quy trình trước khi đầu tư tự động hóa.

## Danh mục chiến dịch và kiểu video

Cả hai loại chiến dịch thuộc phạm vi sản phẩm. Mỗi video gắn với một kênh, một chiến dịch và một kiểu dựng. Chiến dịch Affiliate có thêm sản phẩm. Có thể tạo nhiều kịch bản và nhiều biến thể cho cùng chiến dịch hoặc sản phẩm.

### Community Growth

Dùng để giới thiệu kênh, kết nối creator và xây dựng cộng đồng. Chiến dịch này không yêu cầu sản phẩm Affiliate. Tương tác diễn ra thủ công trên TikTok.

- **CG01 · Channel Introduction** — Giới thiệu kênh và nội dung chính.
- **CG02 · Follow Chéo Community** — Mời người xem giao lưu và kết nối.
- **CG03 · Creator Networking** — Kết nối với creator cùng chủ đề.
- **CG04 · Follower Milestone** — Chia sẻ cột mốc người theo dõi.
- **CG05 · Community Appreciation** — Cảm ơn cộng đồng.

### Affiliate Marketing

Dùng để giới thiệu sản phẩm. Người đăng đối chiếu và gắn đúng sản phẩm trong TikTok.

- **M01 · Product Showcase** — Trình bày sản phẩm. Giọng đọc tùy chọn.
- **M02 · AI Voice Review** — Giới thiệu hoặc đánh giá bằng giọng AI. Có giọng đọc.
- **M03 · Cinematic Product** — Dựng hình sản phẩm theo phong cách điện ảnh. Giọng đọc tùy chọn.
- **M04 · Problem / Solution** — Trình bày vấn đề và cách sản phẩm giải quyết. Có giọng đọc.
- **M05 · Feature Highlights** — Làm nổi bật các tính năng. Có giọng đọc.
- **M06 · Top Benefits** — Tóm tắt các lợi ích chính. Có giọng đọc.
- **M07 · Photo Slideshow** — Ghép ảnh sản phẩm và chữ trên màn hình. Giọng đọc tùy chọn.
- **M08 · UGC Storytelling** — Kể chuyện theo phong cách nội dung người dùng. Có giọng đọc.
- **M09 · Comparison** — So sánh sản phẩm theo các tiêu chí có thể kiểm chứng. Có giọng đọc.
- **M10 · Viral Hook / Fast Cut** — Mở đầu thu hút và cắt cảnh nhanh. Giọng đọc tùy chọn.

## Phạm vi đợt thử đầu

- Chọn một kênh TikTok đã có quyền gắn sản phẩm Affiliate và một sản phẩm để thử.
- Dùng ChatGPT hiện có để soạn 5 kịch bản theo lô, gồm các cảnh, chữ trên video, caption và hashtag.
- Dùng FFmpeg trên máy hiện tại để dựng video dọc 9:16 từ ảnh sản phẩm có quyền sử dụng. Mẫu đầu tiên dùng chữ trên màn hình và có thể chạy không cần giọng đọc.
- Lưu media và MP4 cục bộ. Dùng danh sách trong Odoo nếu hệ thống đã chạy. Nếu chưa có Odoo, dùng CSV cho đợt thử.
- Kiểm tra bản dựng, tải video lên TikTok, gắn sản phẩm và đăng thủ công trong ứng dụng.

## Quy trình thực hiện

1. Ghi tên sản phẩm, tên shop, link sản phẩm và TikTok Product ID hoặc SKU nếu có. Chuẩn bị ảnh nguồn và kiểm tra các thông tin sẽ dùng trong quảng cáo.
2. Đưa dữ liệu sản phẩm vào ChatGPT. Yêu cầu mỗi kịch bản có danh sách cảnh với ảnh, chữ hiển thị và thời lượng, kèm caption và hashtag. Có thể sao chép kết quả dưới dạng JSON để dùng lại khi dựng. Duyệt nội dung trước khi render.
3. Dựng MP4 bằng FFmpeg. Kiểm tra video trên điện thoại để xác nhận chữ dễ đọc, đúng ảnh và đúng sản phẩm.
4. Chuyển MP4 sang điện thoại. Trong TikTok, tải video, dán caption, đối chiếu tên shop và sản phẩm, gắn sản phẩm rồi đăng.
5. Sau khi xác nhận bài đã đăng và có đúng sản phẩm, cập nhật trạng thái, link bài và thời điểm đăng. Ghi số phút xử lý thủ công để xác định bước nào đáng tự động hóa.

## Dữ liệu theo dõi

Mỗi dòng đại diện cho một video. Có thể dùng cùng các cột trong Odoo hoặc CSV.

- **Nhận diện** — mã video, kênh, loại chiến dịch, mã kiểu video và thông tin sản phẩm nếu là Affiliate.
- **Media** — đường dẫn MP4, caption và hashtag.
- **Trạng thái** — Nháp → Đã dựng → Đã duyệt → Đã đăng. Ghi lỗi hoặc việc cần sửa nếu video chưa thể chuyển bước.
- **Kết quả** — link bài TikTok, thời điểm đăng và số phút thao tác thủ công.

Chỉ ghi **Đã đăng** khi đã kiểm tra bài trên TikTok. Mỗi video được đối chiếu với sản phẩm đã chọn trước khi tính vào kết quả thử nghiệm.

## Chi phí dự kiến

Mục tiêu là **0 đồng phí dịch vụ mới trong đợt thử**, với điều kiện đã có ChatGPT, máy chạy FFmpeg và đủ dung lượng lưu file. Vẫn cần tính thời gian duyệt, dựng, chuyển file và đăng.

ChatGPT được dùng trực tiếp để soạn nội dung. Nếu cần tích hợp AI vào Odoo sau này, OpenAI API có hệ thống tính phí riêng. [Hướng dẫn thanh toán của OpenAI](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform)

## Tiêu chí nghiệm thu

- Dựng và duyệt được 5 video bằng cùng mẫu slideshow.
- Cả 5 video đã đăng trên kênh thử nghiệm và đã xác nhận gắn đúng sản phẩm.
- Có đủ link bài đăng, thời điểm đăng và số phút thao tác cho từng video.
- Xác định được bước tốn nhiều thời gian nhất từ dữ liệu thực tế.

## Sau đợt thử

- Dùng chung cấu trúc kịch bản theo cảnh và quy trình FFmpeg cho hai loại chiến dịch. Sau M07, thử CG01 và M01 bằng cách tái sử dụng mẫu ảnh và chữ. Bổ sung các kiểu còn lại theo nhu cầu của từng kênh.
- Dùng ZeroTTS khi triển khai nhóm cần giọng đọc. Tạo audio theo từng cảnh và dùng thời lượng audio để căn chữ và chuyển cảnh.
- Mở thêm hai kênh sau khi quy trình chạy ổn định. Ưu tiên kiểu video theo bản gốc:
  - **Home & Living** — M02, M04, M05, M06, M10.
  - **Beauty** — M01, M02, M03, M06, M08.
  - **Technology** — M02, M05, M09, M10.
- Cân nhắc R2 khi cần chia sẻ media giữa các máy. Cân nhắc OpenAI API khi thao tác nhập kịch bản thủ công trở thành điểm nghẽn.
- Xác minh khả năng được cấp quyền `video.upload` cho trường hợp sử dụng nội bộ trước khi đầu tư OAuth và TikTok Inbox. Việc gắn sản phẩm và đăng bài vẫn do người dùng thực hiện trong TikTok. [Tài liệu TikTok Upload](https://developers.tiktok.com/docs/en/content-posting-api-reference-upload-video)
- Hoãn dashboard, cảnh báo Telegram và giám sát kênh đến khi khối lượng vận hành cần các tính năng này.
