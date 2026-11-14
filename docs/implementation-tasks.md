# Backlog triển khai TikTok Affiliate Studio

Phạm vi theo [đặc tả MVP](mvp.md). Repo hiện chỉ có tài liệu. Đề xuất dựng bản chạy cục bộ bằng Python và FFmpeg trước, dùng ChatGPT để tạo kịch bản theo lô và đưa file JSON vào công cụ. Việc chọn kênh đủ điều kiện, chuẩn bị ảnh, gắn sản phẩm và đăng bài là đầu vào hoặc thao tác vận hành.

## Đợt 1 · Đường chạy hoàn chỉnh cho M07

### T01 · Tạo CLI và cấu hình thư mục

- Đầu ra gồm điểm chạy `python -m affiliate_studio`, lệnh `doctor` kiểm tra FFmpeg và ffprobe, cấu hình thư mục media và export.
- Dùng thư viện chuẩn Python cho CLI và JSON. Bỏ qua media thật và file dựng trong Git.
- Nghiệm thu khi chạy được `--help`, báo rõ công cụ nào thiếu và trả mã lỗi khi môi trường chưa sẵn sàng.

### T02 · Định nghĩa JSON kịch bản và kiểm tra đầu vào

- Giữ một ví dụ JSON và một prompt ChatGPT tạo đúng cấu trúc. Mỗi video có `video_id`, `channel_id`, `campaign_type`, `mode`, `caption`, `hashtags` và `scenes`. Mỗi cảnh có `asset`, `text` và `duration_seconds`. Affiliate yêu cầu thông tin sản phẩm gồm tên, shop và URL hoặc mã TikTok.
- Kiểm tra mã mode phù hợp loại chiến dịch, đường dẫn ảnh nằm trong thư mục media cấu hình, danh sách cảnh có dữ liệu và thời lượng hữu hạn, dương. Báo lỗi theo cảnh và trường dữ liệu.
- Nghiệm thu bằng một JSON M07 hợp lệ và các mẫu thiếu ảnh, sai mode, sai thời lượng hoặc thiếu sản phẩm. Phụ thuộc T01.

### T03 · Dựng M07 bằng FFmpeg

- Thêm lệnh `render <script.json>`. Chuẩn hóa ảnh dọc, giữ tỷ lệ ảnh, xuống dòng chữ tiếng Việt và nối cảnh. Dùng font hỗ trợ dấu tiếng Việt và cho phép cấu hình đường dẫn font.
- Xuất MP4 H.264, kích thước 1080×1920. Gọi FFmpeg bằng danh sách đối số. Dựng vào file tạm và chỉ đưa ra thư mục export khi render thành công. Giữ bản xuất hiện có nếu lần dựng lại lỗi.
- Nghiệm thu bằng ffprobe và xem trên điện thoại. Video có đủ cảnh, chữ tiếng Việt dễ đọc và thời lượng khớp kịch bản trong sai số một khung hình mỗi cảnh. Phụ thuộc T02.

### T04 · Ghi nhận duyệt và đăng thủ công

- Dùng CSV, mỗi video có một dòng theo `video_id`. Ghi đường dẫn MP4, kênh, chiến dịch, mode, thông tin sản phẩm, caption, hashtag, trạng thái và thời gian xử lý.
- Hỗ trợ luồng Nháp → Đã dựng → Đã duyệt → Đã đăng. Khi người dùng xác nhận đăng, yêu cầu link bài và thời điểm đăng. Cập nhật theo mã video để chạy lại lệnh không tạo dòng trùng. CSV MVP do một người cập nhật tại một thời điểm.
- Nghiệm thu khi có thể đi hết luồng, tìm lại video cần đăng cùng thông tin gắn sản phẩm và chạy lại thao tác mà vẫn giữ một dòng cho video. Phụ thuộc T02–T03.

### T05 · Chạy thử đầu cuối

- Dựng lại từ ví dụ với ảnh thử, sau đó chạy lô 5 kịch bản M07 với tư liệu của sản phẩm thật.
- Nghiệm thu phần code khi xuất được 5 MP4 và theo dõi được cả lô. Hoàn tất đợt thử sau khi người dùng xác nhận đủ 5 bài TikTok đã gắn đúng sản phẩm và ghi thời gian thao tác. Phụ thuộc T01–T04.

## Đợt 2 · Hỗ trợ hai chiến dịch và đủ 15 kiểu video

### T06 · Dùng chung cấu trúc cảnh cho hai chiến dịch

- Đăng ký danh mục CG01–CG05 và M01–M10 theo đặc tả, kèm đầu vào bắt buộc và chế độ giọng đọc. Trả lỗi rõ nếu chọn một kiểu đã có trong danh mục nhưng chưa có mẫu dựng.
- Làm CG01 và M01 trên bộ dựng hiện có. Cho phép Community Growth đi từ kịch bản đến xác nhận đăng mà không cần thông tin sản phẩm.
- Nghiệm thu khi M07 vẫn chạy và có thêm MP4 mẫu cho CG01 và M01. Phụ thuộc T05.

### T07 · Tích hợp giọng đọc

- Xác nhận bản ZeroTTS, cách gọi, khả năng đọc tiếng Việt và chi phí thực tế. Thử một cảnh tiếng Việt trước khi tích hợp.
- Tạo audio theo cảnh, dùng ffprobe đo thời lượng để căn chữ và cảnh, ghép audio vào MP4. Thử đầu cuối với M02. Dùng lại audio nếu nội dung và cấu hình giọng đọc trùng.
- Nghiệm thu khi M02 có audio rõ, cảnh khớp lời đọc và kiểu có giọng đọc bắt buộc báo lỗi nếu tạo audio thất bại. Phụ thuộc T06.

### T08 · Hoàn thiện mẫu và prompt cho các kiểu còn lại

- Làm CG02, CG03, CG04, CG05, M03, M04, M05, M06, M08, M09 và M10. Với mỗi kiểu, định nghĩa nhịp cảnh, tư liệu, bố cục chữ và yêu cầu giọng đọc dựa trên đặc tả.
- Tái sử dụng trình dựng, bước kiểm tra dữ liệu và lớp tạo audio. Chỉ bổ sung khả năng dựng khi mẫu thực sự cần, chẳng hạn nhịp cắt ngắn cho M10.
- Nghiệm thu khi chạy được ít nhất một ví dụ cho từng mã CG01–CG05 và M01–M10. Phụ thuộc T06 và T07 đối với các kiểu cần giọng đọc.

## Đợt 3 · Mở rộng khi có nhu cầu vận hành

- **T09 · Đa kênh và Odoo.** Thêm cấu hình riêng theo kênh, sau đó làm danh sách kênh, sản phẩm và video trong Odoo nếu CSV đã thành điểm nghẽn. Dùng lại CLI dựng video và kiểm tra dữ liệu của ba kênh được lọc đúng.
- **T10 · Tích hợp theo điểm nghẽn.** Chọn OpenAI API nếu nhập kịch bản mất nhiều thời gian, R2 nếu cần chia sẻ media, hoặc TikTok Inbox sau khi xác minh quyền `video.upload`. Đánh giá từng tích hợp từ số liệu đợt thử. Với Inbox, chỉ ghi nhận Đã đăng sau khi người dùng xác nhận bài đăng thực tế.

Bắt đầu bằng T01 và T02. Lấy một bộ ảnh mẫu và một kịch bản M07 để làm đầu vào cho T03, sau đó khép luồng với T04 trước khi chạy thử 5 video.
