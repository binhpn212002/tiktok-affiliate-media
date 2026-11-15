# Import kịch bản, tạo giọng đọc và dựng video TikTok

Trong **Affiliate Video**, dán JSON vào **Script JSON**, lưu bản nháp rồi bấm **Render**. Odoo xử lý hàng đợi bằng tác vụ nền. Tải lại bản ghi để xem trạng thái và tải MP4.

## Các task triển khai

1. **Nhận kịch bản** — Dán JSON vào bản nháp, kiểm tra cấu trúc và xác định ảnh R2 cho từng cảnh. JSON lỗi bị từ chối trước khi xếp hàng.
2. **Xử lý nền** — Nút Render xếp video vào hàng đợi Odoo. Bấm lại khi đang chờ chỉ giữ một lượt dựng. Trường Render Status và Render Error cho biết kết quả.
3. **Dựng và lưu MP4** — Tải ảnh từ R2, tạo WAV bằng ZeroTTS, dựng bằng FFmpeg rồi upload MP4 lên R2. Chỉ cập nhật trạng thái Rendered khi MP4 hợp lệ.

## Quy trình sử dụng

1. Chuẩn bị thông tin sản phẩm và ảnh được phép sử dụng. Nhờ ChatGPT soạn kịch bản JSON theo cấu trúc bên dưới ngay trong cửa sổ chat. Kiểm tra lời đọc, ảnh và các thông tin về sản phẩm.
2. Trong Odoo, tạo **Affiliate Video**, chọn chiến dịch và chọn sản phẩm nếu là chiến dịch Affiliate Marketing. Dán JSON vào **Script JSON**. Khi bấm **Render**, Odoo kiểm tra dữ liệu và lấy caption, hashtag từ JSON nếu có.
3. Bấm **Render**. Worker tải ảnh từng cảnh, dùng ZeroTTS cục bộ để tạo WAV từ lời đọc, rồi dùng FFmpeg ghép ảnh và âm thanh thành MP4 dọc.
4. Xem MP4, kiểm tra ảnh và giọng đọc rồi duyệt video. Tải MP4 lên TikTok, dán caption và hashtag, gắn sản phẩm và đăng thủ công.

Người dùng thao tác trực tiếp trong ChatGPT. Odoo chỉ nhận nội dung đã soạn. Luồng này không cần OpenAI API, trường Prompt hay Video Template.

## JSON nhập vào Odoo

```json
{
  "title": "Bình giữ nhiệt 500 ml",
  "caption": "Một chiếc bình gọn để mang theo mỗi ngày.",
  "hashtags": ["#binhgiunhiet", "#dodungcanhan"],
  "scenes": [
    {
      "sequence": 1,
      "narration": "Bạn đang tìm một chiếc bình gọn để mang đi làm?",
      "image_index": 1
    },
    {
      "sequence": 2,
      "narration": "Mẫu này có dung tích năm trăm mi-li-lít.",
      "image_index": 2
    }
  ]
}
```

Thêm ảnh vào sản phẩm trước. `image_index` bắt đầu từ 1, theo thứ tự ảnh được thêm. Có thể dùng `image_url` thuộc domain R2 đã cấu hình thay cho `image_index`. Khi import, kiểm tra JSON hợp lệ, có ít nhất một cảnh, số thứ tự là số nguyên dương và không trùng, lời đọc không rỗng và mỗi cảnh chọn được một ảnh từ R2. Báo lỗi theo số cảnh để người dùng sửa. Nếu dữ liệu không hợp lệ, giữ nguyên bản ghi hiện tại. Kênh, chiến dịch và sản phẩm vẫn được chọn trong Odoo.

## Xử lý TTS và FFmpeg

- **TTS** đọc `narration` của mỗi cảnh, tạo một WAV và lấy thời lượng thực của âm thanh để xác định độ dài cảnh. Giọng đọc lấy từ cấu hình kênh hoặc mặc định của worker. Luồng này tự tạo WAV, nên bước import chỉ cần JSON.
- **FFmpeg** ghép từng ảnh với WAV tương ứng rồi nối các cảnh theo thứ tự. Xuất MP4 dọc 9:16 ở 1080 × 1920, 30 fps, với H.264 và AAC.
- **Odoo** ghi đường dẫn MP4 và chuyển video sang **Rendered** sau khi worker xác nhận file hợp lệ. Nếu tải ảnh, tạo WAV hoặc render thất bại, giữ video ở **Draft**, hiển thị bước lỗi và cảnh liên quan để người dùng sửa rồi thử lại. Mỗi video chỉ có một job render đang chờ hoặc đang chạy.

## Chạy trên máy local

Môi trường Python của Odoo cần có `zerotts` và `soundfile`; máy chạy Odoo cần có `ffmpeg` và `ffprobe` trong PATH. ZeroTTS tải model trong lần đầu nếu máy chưa có cache. Nạp `R2_PUBLIC_BASE_URL` vào môi trường Odoo để tác vụ nền tải ảnh. MP4 mới được lưu trong thư mục `videos/` của bucket R2. Odoo lưu URL trong **Video Path**.

## Mã tham khảo trong `video_youtube_tiktok`

- Import và kiểm tra JSON trong `video_automation/wizard/video_script_import.py`.
- Tạo WAV cục bộ trong `video_tool/worker/app/tts_service.py`.
- Dựng MP4 dọc trong `video_tool/worker/app/ffmpeg_renderer.py`.
- Điều phối tải ảnh, TTS và render trong `video_tool/worker/app/main.py`.
