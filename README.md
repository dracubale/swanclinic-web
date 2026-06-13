# Swan Clinic — Website

Website chính thức của **CÔNG TY TNHH SWAN CLINIC** — Phòng khám chuyên khoa thẩm mỹ, TP. Hồ Chí Minh.
Live: https://swanclinic.vn

## Cấu trúc
- `index.html` — toàn bộ trang (HTML/CSS/JS thuần, 1 file)
- `img/` — hình ảnh (logo, bác sĩ, dịch vụ, không gian phòng khám)

## Tính năng
- Trang 1 trang (one-page) responsive: Giới thiệu · Dịch vụ · Không gian · Bảng giá · Đội ngũ bác sĩ · Liên hệ
- 7 ngôn ngữ (mặc định Tiếng Việt): VI · EN · TH · ZH · FR · KO · KM
- Nút "Đặt hẹn" mở Messenger; bản đồ Google Maps; thông tin pháp lý đầy đủ

## Deploy (nginx)
```bash
sudo cp -r index.html img /var/www/swanclinic/
sudo systemctl reload nginx
```

## Cập nhật nội dung
Sửa text/bản dịch trong `index.html` (phần `var T = {...}`), thay ảnh trong `img/`, rồi commit & push.
