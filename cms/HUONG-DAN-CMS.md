# Swan Clinic CMS — Hướng dẫn cài đặt & sử dụng

## CMS là gì?
Trang quản trị tại **https://swanclinic.vn/admin** để nhân viên tự cập nhật website
(không cần sửa code): đăng bài Tin tức, upload văn bằng bác sĩ, giấy phép, sửa giá & liên hệ.

## Cài đặt (chạy 1 lần trên droplet)
1. Upload thư mục `cms/` lên server (WinSCP → `/tmp/cms/`)
2. PuTTY:
   ```
   cd /tmp/cms && bash install.sh
   ```
3. Mở nginx config: `nano /etc/nginx/sites-available/swanclinic.vn`
   → dán 2 block trong `nginx-admin.conf` vào TRONG `server { ... }` (bản 443/ssl)
4. `nginx -t && systemctl reload nginx`
5. Vào https://swanclinic.vn/admin — đăng nhập: **admin / SwanClinic@2026**
   → **ĐỔI MẬT KHẨU NGAY** trong tab ⚙️ Cài đặt.

## Nhân viên dùng thế nào?
- **📰 Tin tức**: Viết bài mới → chọn 1 trong 3 chuyên mục (Tin tức Swan Clinic /
  Giáo dục sức khỏe & Làm đẹp / Chính sách, pháp luật y tế) → nhập tiêu đề, nội dung
  (mỗi đoạn cách 1 dòng trống), ảnh bìa, ảnh kèm → Lưu. Có thể Ẩn/Hiện/Sửa/Xoá.
- **👨‍⚕️ Bác sĩ**: upload ảnh văn bằng, GPHN, chứng chỉ CME cho từng bác sĩ
  (⚠️ làm mờ thông tin cá nhân trước khi upload). Website hiện nút
  "Văn bằng & chứng chỉ" trên thẻ bác sĩ.
- **📜 Pháp lý**: upload ảnh GPHĐ (che số nếu cần) → hiện ở mục Giới thiệu.
  Danh mục kỹ thuật: upload ảnh/PDF, có công tắc ẨN/HIỆN (mặc định ẩn, mở khi cần).
- **⚙️ Cài đặt**: hotline, email, link Messenger (nút Đặt hẹn), bảng giá 6 dịch vụ.
- **👥 Tài khoản** (chỉ admin): tạo/xoá tài khoản nhân viên.

## Ghi chú kỹ thuật
- Nội dung lưu tại `/var/www/swanclinic/content/` (JSON + uploads) — NGOÀI git,
  không bị deploy-swan ghi đè. Backup: nén thư mục này.
- CMS chạy service `swan-cms` (port nội bộ 8300). Lệnh: `systemctl status swan-cms`,
  log: `journalctl -u swan-cms -n 50`.
- Ảnh upload tự resize ≤1600px để web nhẹ. Giới hạn 10MB/file.
