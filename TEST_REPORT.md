# Báo cáo kiểm thử

Chạy: `python -m unittest discover -s tests -t . -v` → **95 test, tất cả đạt** (khoảng 3 giây, Python 3.12, SQLite 3.45).

| Nhóm | File | Số test | Phạm vi |
|---|---|---|---|
| Nền tảng | `tests/test_core.py` | 13 | Migration (áp một lần, đúng thứ tự), khóa ngoại, giao dịch/savepoint rollback, sao lưu nóng + dọn bản cũ, chống spam (cooldown + chặn tạm), tạo nhân vật, lên cấp, chết/Hình Nhân, mất kiểm soát, hồi phục theo thời gian, **xóa nhân vật** (dọn quỷ/nhiệm vụ/báo cáo, hoàn quỹ, khóa ngoại sạch), dọn bộ nhớ chống spam |
| Lệ quỷ & Ngự Quỷ Giả | `tests/test_ghosts.py` | 25 | 6 cơ chế đối mặt riêng (thắng/thua/khiên/vật phẩm), dữ liệu quỷ đầy đủ + vòng khắc chế khép kín, khống chế & tỷ lệ, khe chứa, phục tô theo thời gian → sự kiện thế giới, khắc chế/mất cân bằng/xung đột, năng lực, thức tỉnh, quá nhiệt gây phục tô, phong ấn/bàn giao, bách khoa theo manh mối, cứu đồng đội, luồng đối mặt đầy đủ (lưu DB), bỏ chạy |
| Thế giới & sự kiện | `tests/test_world.py` | 20 | Đồ thị địa điểm, di chuyển (cấp/Tổng Bộ/phong tỏa/sự kiện), khám phá (chi phí, cooldown, mọi loại kết quả, buff), 6 loại sự kiện (đóng góp thành công/thất bại, toàn máy chủ, giới hạn thời gian, tick sinh sự kiện, phai nguy hiểm, thưởng đội hình ≥3 người), cốt truyện nhiều kết cục, **chuỗi liên kết** quỷ phục tô → sự kiện → thất bại → phong tỏa |
| Xã hội & kinh tế | `tests/test_social.py` | 19 | Phân quyền cấp bậc, nhiệm vụ tổ chức (ký quỹ, tiến độ qua sự kiện thật, hết hạn hoàn quỹ), báo cáo (không tự duyệt, giới hạn/ngày), mở phong tỏa, cửa hàng, nghỉ ngơi, giao dịch nguyên tử (thất bại không đổi gì), nhiệm vụ & thành tựu liên kết, bảng xếp hạng, **Hồ sơ linh dị** (kho giam giữ, phí theo cấp, cooldown, không tác dụng phụ khi lỗi) |
| Tài nguyên | `tests/test_assets.py` | 5 | 35 PNG khớp `emoji_map.json`, đúng 128×128 RGBA ≤256 KiB, tên hợp lệ, **mọi tên emoji được mã nguồn tham chiếu đều tồn tại** (quét AST), đủ nhóm theo yêu cầu, vẽ lại cho đúng từng byte |
| Lớp Discord (giả lập) | `tests/test_discord_smoke.py` | 13 | Nạp 8 Cog, 25 lệnh gốc + 39 lệnh con thỏa ràng buộc Discord, đồng bộ emoji (idempotent, giãn cách, từ chối file hỏng), hành trình người chơi qua nút/menu thật, phân quyền admin, chống spam, thông báo lỗi thân thiện, Embed ở nội dung tối đa, **fuzz 15 người chơi** (562 lượt khám phá, 378 bước đối mặt, 21 lần sống sót, DB `integrity_check` = ok, `foreign_key_check` sạch) |

## Lỗi tìm thấy nhờ kiểm thử (đã sửa)
1. **Hồ sơ bị cắt nội dung với ID emoji thật**: ID emoji Discord dài 19 chữ số nên thanh tiến trình rất dài; field "Sinh tồn" vượt 1024 ký tự và `cut()` làm mất dòng cuối. Đã tách thành từng field riêng; test Embed nội dung tối đa chặn tái phát.
2. Chống spam chặn đúng khi test bắn hàng chục lệnh liên tiếp (hành vi mong muốn; test được chỉnh để giả lập thời gian).
3. **Xóa nhân vật vi phạm ràng buộc DB**: `ON DELETE SET NULL` trên chủ sở hữu lệ quỷ đụng CHECK, và người từng giao nhiệm vụ bị khóa ngoại chặn. Phát hiện khi rà lược đồ và tái hiện bằng script; đã thêm `PlayerService.delete` dọn đúng thứ tự (có test).
4. **Cân bằng**: mô phỏng 20.000 lần cho thấy Quỷ Nhãn quá khắc nghiệt (6%), Quỷ Vực dễ hơn quỷ hạng thấp, biết quy luật là hết rủi ro, giai đoạn đầu cháy túi. Đã chỉnh (xem `docs/BALANCE.md`).
5. Nhiều giả định sai trong chính các test (tên 1 ký tự bị chặn, xuất thân đã có đồ...) được sửa ở test, không phải ở engine.

## Chưa kiểm thử / giới hạn trung thực
- **Chưa chạy với discord.py thật và Discord thật** (môi trường làm việc không có thư viện và không có mạng). Lớp Cog được kiểm thử qua bộ giả lập `tests/fake_discord.py`, nó mô phỏng các ràng buộc quan trọng (tên/mô tả lệnh, 25 lựa chọn, 5 dòng thành phần, giới hạn Embed...) nhưng **không** bảo đảm mọi chi tiết API thật (đặc biệt `create_application_emoji`, vốn cần discord.py ≥ 2.5: các giới hạn emoji đã đối chiếu với tài liệu Discord nhưng chữ ký hàm chưa đọc từ tài liệu discord.py chính thức; và cách Discord hiển thị emoji ứng dụng).
- Chưa kiểm thử tải thật (nhiều người dùng đồng thời trên một máy chủ Discord), chưa kiểm thử khởi động lại giữa lúc đang đối mặt trên bot thật (logic lưu trạng thái đã được test ở tầng engine).
- Cân bằng game mới qua mô phỏng (chính sách ngẫu nhiên là cận dưới rất khắc nghiệt), **chưa qua chơi thử với người thật**. Quỷ Vực (hạng A) vẫn không khó hơn quỷ hạng B với người mù, đã ghi trong `docs/BALANCE.md`.
- Emoji: đã xem ở 128 px và thu nhỏ 32 px (đọc được), nhưng chưa xem trên giao diện Discord thật (nền sáng/tối).
