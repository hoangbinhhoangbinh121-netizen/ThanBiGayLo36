# Thiết kế game (toàn bộ là thiết lập riêng; xem REFERENCES.md)

## Vòng chơi
Khám phá nơi nguy hiểm → thu **manh mối** (quyết định sống/chết) → đối mặt lệ quỷ bằng cơ chế riêng của nó → sống sót thì **khống chế** (thành Ngự Quỷ Giả) hoặc **phong ấn** (cần Vật Chứa Vàng) hoặc rời đi → dùng năng lực nhưng lệ quỷ **phục tô** → giữ cân bằng, áp chế, nghỉ ngơi → sự kiện thế giới và Tổng Bộ kéo mọi người vào chung một câu chuyện.

## Chỉ số sinh tồn
Thể chất (0 = chết), Tinh thần (0 = sụp đổ → mất kiểm soát 15 phút), Nhiễm linh dị (≥40 thành "nhiễm linh dị": hồi tinh thần chậm, dễ gặp quỷ, phục tô nhanh hơn x1.25), Danh tiếng, EXP/Cấp (cần 100×cấp EXP), Tiền cổ. Hồi phục theo thời gian thực (nhanh gấp đôi ở nơi an toàn). Chết: hồi sinh ở Khu Trung Tâm, mất 30% tiền, 20% EXP, +10 nhiễm linh dị, lệ quỷ đang giữ +20 phục tô; **Hình Nhân Thế Mạng** cứu một lần.

## Sáu lệ quỷ — mỗi con một máy trạng thái khác nhau
| Quỷ (hạng) | Quy luật | Lời giải | Ai biết manh mối được gì |
|---|---|---|---|
| Quỷ Thủ (B) | Siết chặt kẻ chống cự | Đứng yên 3 nhịp; không giãy giụa/nhìn xuống | Hiện đồng hồ độ siết |
| Quỷ Ảnh (C) | Chỉ dẫm bóng kẻ đứng dưới ĐÚNG MỘT nguồn sáng | Chọn chỗ tối hẳn hoặc hai đèn, 4 vòng, bị dẫm 2 lần là chết | Đánh dấu "nơi nó chờ" |
| Quỷ Nhãn (B) | Nhìn quá 3 nhịp thì bị nuốt; nhắm mắt thì nó tiến gần | Luân phiên lùi/nhắm để khoảng cách (xuất phát 4) đạt 6 | Hiện bộ đếm ánh nhìn và khoảng cách |
| Quỷ Quan Tài (B) | Mời nằm vào; nắp chỉ đóng khi có thứ nằm thay | Đóng nắp 3 lần (cần tinh thần ≥12) hoặc dùng vật thế/đinh vàng | Hiện độ khép nắp |
| Quỷ Môn (C) | Gõ LẺ là của nó, gõ CHẴN là người sống | Im lặng với lẻ, mở với chẵn | Hiện chẵn/lẻ |
| Quỷ Vực (A) | Không khí (5) cạn dần; không thể chạy; phá sai neo tốn 3 | Thăm dò tìm neo rồi phá đúng neo | Hiện trục chứa neo |
Không có manh mối thì mọi lựa chọn là canh bạc; có manh mối thì là trò giải đố (số liệu ở `docs/BALANCE.md`). Mỗi vòng còn có xác suất "linh dị dao động" làm hao tinh thần ngay cả khi chơi đúng; sống sót thưởng EXP và tiền cổ. Gương Nứt, Bùa, Đèn Dầu, Hình Nhân... mở thêm lựa chọn riêng cho từng mechanic.

## Ngự Quỷ Giả
- **Khống chế**: tỷ lệ = (nền theo hạng [C 70% / B 50% / A 30% / S 12%] + 10%/manh mối + 25% nếu đang giữ quỷ khắc chế) × (0,6 + 0,4 × tỷ lệ tinh thần) − 0,2% × nhiễm linh dị + bonus cách hạ nó (đinh vàng +30%, bùa dán cửa +20%...). Chặn trong 5%–95%.
- **Khe chứa**: 1 + cấp/12 (tối đa 4). Giữ vượt khe: +10 nhiễm linh dị và phục tô nhanh thêm 50%/quỷ vượt.
- **Phục tô**: mỗi quỷ có tốc độ riêng /giờ; nhân hệ số: mất cân bằng (|tổng cực tính| ≥3) x1.5, bị quỷ khác khắc chế x0.5, xung đột x1.4, có Quỷ Vực x1.3, nhiễm linh dị x1.25, thức tỉnh x0.8. Dùng năng lực cộng thêm trực tiếp. Đạt 100%: quỷ thoát, chủ nhân mất kiểm soát, sinh sự kiện "Lệ Quỷ Phục Tô" tại chỗ.
- **Áp chế**: Bùa Áp Chế (−30), nghỉ ngơi 15 tiền cổ (−10), năng lực Quỷ Quan Tài (−35), đồng đội cứu người mất kiểm soát.
- **Thức tỉnh**: dùng năng lực 6 lần khi phục tô <60% → năng lực mạnh gấp đôi, rẻ hơn 30%.
- **Vòng khắc chế**: Thủ→Ảnh→Nhãn→Môn→Quan Tài→Thủ.

## Thế giới & sự kiện
8 địa điểm với mức nguy hiểm, bảng quỷ xuất hiện, bảng rơi đồ, sự cố riêng; phong tỏa có hạn; nguy hiểm tăng theo sự kiện thất bại và tự phai 1 bậc/6 giờ; "Bất ổn linh dị" toàn cục tăng xác suất sinh sự kiện. Loại sự kiện: **phục tô / quỷ xuất hiện / khẩn cấp** (cùng góp điểm; từ 3 người tham gia thì mỗi hành động +1 đội hình, thành công: thưởng chia theo đóng góp, người nhiều nhất nhận Vật Chứa Vàng và lệ quỷ niêm phong; thất bại: phong tỏa khu vực, người tham gia bị thương), **toàn máy chủ** (Đêm Trăng Máu, Sương Mù), **giới hạn thời gian** (Chuyến Tàu Cuối mở Ga Cuối 1 giờ; kẹt lại bị phạt), **nhiều kết cục** (Bức Thư Từ Người Đã Chết: 4 kết cục, tác động địa điểm/bất ổn).

## Tổ chức
Cấp: Thành Viên → Đội Trưởng (20 danh tiếng) → Người Phụ Trách Khu Vực (60) → Tổng Bộ (bổ nhiệm bởi admin). Chỉ thăng được lên cấp THẤP HƠN cấp mình; chỉ giáng/loại người cấp thấp hơn; Phụ Trách chỉ quản khu vực mình. Đội Trưởng+ giao nhiệm vụ (thưởng trừ từ ngân quỹ, hết hạn hoàn quỹ); Phụ Trách+ duyệt báo cáo (không tự duyệt), mở phong tỏa (150 ngân quỹ). **Hồ sơ linh dị**: mỗi Vật Chứa Vàng bàn giao được lưu vào kho giam giữ và mở hồ sơ về loại quỷ đó cho toàn tổ chức; thành viên trả phí (40 / 20 / miễn phí theo cấp) để đọc hồ sơ và nhận manh mối chưa biết. Chỉ thành viên vào được Phố Cổ và bàn giao Vật Chứa Vàng.

## Sơ đồ liên kết hệ thống
Mọi hệ thống phát sự kiện lên `EventBus` (`explored`, `clue_found`, `encounter_survived`, `bound`, `ghost_sealed`, `resurrected`, `event_joined`, `report_approved`, `trade_done`...). Nhiệm vụ cá nhân, nhiệm vụ tổ chức, thành tựu, thống kê, bảng xếp hạng đều chỉ là người nghe bus, nên một lần khám phá cập nhật tất cả cùng lúc trong một giao dịch DB. Mọi hiệu ứng (sự cố, kết cục, thưởng) đi qua `apply_effects` duy nhất.
