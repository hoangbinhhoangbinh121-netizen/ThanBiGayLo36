# Cân bằng game (đo bằng mô phỏng)

Chạy lại: `python tools/balance_sim.py 20000`. Mô phỏng chỉ dùng engine thuần (không Discord), seed cố định.

```
quy_thu       | mù: sống sót  26.9%  (sát thương TB khi sống 14.3) | biết: sống sót 100.0%  (sát thương TB khi sống  0.0)
quy_anh       | mù: sống sót  59.1%  (sát thương TB khi sống 23.5) | biết: sống sót 100.0%  (sát thương TB khi sống  8.0)
quy_nhan      | mù: sống sót  26.0%  (sát thương TB khi sống  4.9) | biết: sống sót 100.0%  (sát thương TB khi sống  2.0)
quy_quan_tai  | mù: sống sót  12.5%  (sát thương TB khi sống 48.0) | biết: sống sót 100.0%  (sát thương TB khi sống 48.0)
quy_mon       | mù: sống sót  65.5%  (sát thương TB khi sống 25.0) | biết: sống sót 100.0%  (sát thương TB khi sống  0.0)
quy_vuc       | mù: sống sót  33.3%  (sát thương TB khi sống  5.1) | biết: sống sót 100.0%  (sát thương TB khi sống  0.0)

Kinh tế/phiên (60 phiên, cấp 3 ở Khu Dân Cư, không manh mối, đến khi cạn tinh thần):
  khám phá TB 7.6 lượt  | tiền cổ ròng TB +42  | vật phẩm TB 2.4
  gặp quỷ 90, sống sót 53 (59%), chết 26, khống chế thành công 23
```

## Cách đọc
- **"mù"** = chọn hành động hoàn toàn ngẫu nhiên, không biết quy luật nào. Đây là **cận dưới** rất khắc nghiệt: người thật thường tránh "Nằm vào quan tài" hay "Mở cửa" một cách trực giác, nên sống sót thực tế cao hơn.
- **"biết"** = có đủ 3 manh mối và chơi đúng. Sống sót 100% là **chủ đích**: quy luật của lệ quỷ là trò giải đố, tri thức là phần thưởng. Áp lực còn lại đến từ sát thương cố định (Quỷ Quan Tài tốn ~48), "linh dị dao động" (hao tinh thần mỗi vòng với xác suất 15–45% tùy nguy hiểm khu vực), phí quỷ vực khi bước vào, và rủi ro dài hạn là phục tô.
- Phiên chơi kinh tế: người cấp 3, ở Khu Dân Cư, **không có manh mối**, chơi tới khi cạn tinh thần. Kết quả ~+42 tiền cổ ròng/phiên; người có manh mối kiếm nhiều hơn vì ít chết (chết mất 30% tiền).

## Quyết định cân bằng rút ra từ số liệu
| Phát hiện lần đo đầu | Chỉnh |
|---|---|
| Quỷ Nhãn (hạng B) chỉ 6% cho người mù, khắc nghiệt hơn mọi quỷ khác | Khoảng cách xuất phát 3 → 4 (lên ~26%) |
| Quỷ Vực (hạng A) dễ hơn quỷ hạng B (44%) | Không khí 6 → 5, phá sai neo tốn 3 thay vì 2 (còn ~33%) |
| Biết quy luật là hết rủi ro | Thêm "linh dị dao động" hao tinh thần mỗi vòng |
| Giai đoạn đầu cháy túi (+22 tiền/phiên, nghỉ ngơi 20) | Sống sót đối mặt thưởng tiền (8×hạng + 3×nguy hiểm), nghỉ 20 → 15, tăng tỷ lệ nhặt tiền |

## Điều chưa giải quyết (trung thực)
- Quỷ Vực (A) vẫn không khó hơn Quỷ Thủ/Quỷ Nhãn (B) với người chơi mù. Chấp nhận có chủ đích: theo nguồn cộng đồng, phân cấp C/B/A/S phản ánh **phạm vi lan rộng**, không nhất thiết độ khó đối mặt; Quỷ Vực bù lại bằng việc không thể bỏ chạy, phí vào cao nhất và khuếch đại mọi quỷ khác khi giữ.
- Chưa có dữ liệu người chơi thật. Mọi hằng số nằm ở `data/` và đầu các file `engine/` để chỉnh nhanh.
