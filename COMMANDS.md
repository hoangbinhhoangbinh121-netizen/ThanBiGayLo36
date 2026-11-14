# Danh sách lệnh — Thần Bí Phục Tô

Sinh tự động bằng `python tools/gen_docs.py` từ cây lệnh thật. Dấu * = tham số bắt buộc.

## /admin — Quản trị bot

| Lệnh | Tham số | Mô tả |
|---|---|---|
| `/admin bo_nhiem` | `nguoi`* | Bổ nhiệm một người chơi làm Tổng Bộ |
| `/admin emoji` | — | Tải/đồng bộ bộ emoji pixel art lên Discord (emoji ứng dụng) |
| `/admin kenh` | `kenh`* | Đặt kênh nhận thông báo sự kiện thế giới |
| `/admin mo_khoa` | `dia_diem`* — [Khu Dân Cư Thanh Bình / Bệnh Viện Số Bảy / Trường Trung Học Minh Đức / Nghĩa Trang Bạch Vân / Làng Đoạn Hà / Phố Cổ Lục Môn / Ga Tàu Điện Cuối] | Tháo phong tỏa một địa điểm |
| `/admin sao_luu` | — | Sao lưu cơ sở dữ liệu ngay |
| `/admin su_kien` | `loai`* — [Quỷ Xuất Hiện / Nhiệm Vụ Khẩn Cấp / Đêm Trăng Máu / Sương Mù Dày Đặc / Chuyến Tàu Cuối]<br>`dia_diem` — [Khu Dân Cư Thanh Bình / Bệnh Viện Số Bảy / Trường Trung Học Minh Đức / Nghĩa Trang Bạch Vân / Làng Đoạn Hà / Phố Cổ Lục Môn / Ga Tàu Điện Cuối] | Kích hoạt một sự kiện thế giới |
| `/admin tang` | `nguoi`*<br>`vat_pham`* — [Đèn Dầu Cũ / Cuộn Băng Trắng / Trà An Thần / Bùa Áp Chế / Vật Chứa Vàng / Đinh Quan Tài Vàng / Hình Nhân Thế Mạng / Thư Linh Dị…]<br>`so_luong` | Tặng vật phẩm cho người chơi |
| `/admin thong_ke` | — | Thống kê hệ thống |
| `/admin xoa_nhan_vat` | `nguoi`* | Xóa nhân vật của một người chơi (dọn sạch dữ liệu liên quan) |

- `/ap_che_dong_doi` — Dùng Bùa Áp Chế kéo đồng đội đang mất kiểm soát (cùng địa điểm)  
  Tham số: `nguoi`* — Đồng đội đang mất kiểm soát
- `/ban` — Bán vật phẩm cho cửa hàng  
  Tham số: `vat_pham`* — [Đèn Dầu Cũ / Cuộn Băng Trắng / Trà An Thần / Bùa Áp Chế / Vật Chứa Vàng / Đinh Quan Tài Vàng / Hình Nhân Thế Mạng / Thư Linh Dị…]<br>`so_luong`
- `/ban_do` — Bản đồ thế giới, mức nguy hiểm và các khu phong tỏa
- `/bxh` — Bảng xếp hạng  
  Tham số: `loai`* — [Cấp độ / Danh tiếng / Phong ấn / Manh mối / Cống hiến Tổng Bộ]
- `/cua_hang` — Xem cửa hàng Tổng Bộ (chỉ ở Khu Trung Tâm)
- `/di_chuyen` — Di chuyển tới địa điểm lân cận (tốn tinh thần)
- `/dia_diem` — Xem nơi bạn đang đứng
- `/doi_mat` — Quay lại cuộc đối mặt đang dở với lệ quỷ
- `/dung_vat_pham` — Dùng một vật phẩm trong túi  
  Tham số: `vat_pham`* — [Đèn Dầu Cũ / Cuộn Băng Trắng / Trà An Thần / Bùa Áp Chế / Vật Chứa Vàng / Đinh Quan Tài Vàng / Hình Nhân Thế Mạng / Thư Linh Dị…]
## /giao_dich — Trao đổi vật phẩm và tiền cổ với người chơi khác

| Lệnh | Tham số | Mô tả |
|---|---|---|
| `/giao_dich chap_nhan` | `ma`* | Chấp nhận giao dịch theo mã |
| `/giao_dich danh_sach` | — | Lời mời giao dịch đang chờ bạn |
| `/giao_dich moi` | `nguoi`* — Người nhận<br>`cho_vat_pham` — Bạn đưa vật phẩm [Đèn Dầu Cũ / Cuộn Băng Trắng / Trà An Thần / Bùa Áp Chế / Vật Chứa Vàng / Đinh Quan Tài Vàng / Hình Nhân Thế Mạng / Thư Linh Dị…]<br>`cho_so_luong` — Số lượng bạn đưa<br>`cho_xu` — Tiền cổ bạn đưa<br>`doi_vat_pham` — Bạn muốn nhận vật phẩm [Đèn Dầu Cũ / Cuộn Băng Trắng / Trà An Thần / Bùa Áp Chế / Vật Chứa Vàng / Đinh Quan Tài Vàng / Hình Nhân Thế Mạng / Thư Linh Dị…]<br>`doi_so_luong` — Số lượng muốn nhận<br>`doi_xu` — Tiền cổ muốn nhận | Gửi lời mời giao dịch (người nhận phải chấp nhận) |
| `/giao_dich tu_choi` | `ma`* | Từ chối hoặc hủy giao dịch theo mã |

- `/ho_so` — Xem hồ sơ nhân vật  
  Tham số: `nguoi` — Người chơi muốn xem (mặc định là bạn)
- `/kham_pha` — Khám phá nơi bạn đang đứng: tìm manh mối, vật phẩm, hoặc đối mặt lệ quỷ
- `/kho_do` — Xem túi đồ
- `/lich_su` — Lịch sử sự kiện của bạn
- `/mua` — Mua vật phẩm ở cửa hàng  
  Tham số: `vat_pham`* — [Đèn Dầu Cũ (40) / Cuộn Băng Trắng (25) / Trà An Thần (30) / Bùa Áp Chế (80) / Vật Chứa Vàng (300) / Hình Nhân Thế Mạng (160)]<br>`so_luong` — 1-20
- `/nghi_ngoi` — Nghỉ trong nhà an toàn (15 tiền cổ): hồi sức và giảm phục tô
## /nhiem_vu — Bảng nhiệm vụ

| Lệnh | Tham số | Mô tả |
|---|---|---|
| `/nhiem_vu danh_sach` | — | Bảng nhiệm vụ và tiến độ của bạn |
| `/nhiem_vu nhan` | `nhiem_vu`* — [Điều Tra Lần Đầu / Thu Thập Manh Mối / Sống Sót / Phong Ấn Đầu Tiên / Con Đường Ngự Quỷ / Hồ Sơ Nghĩa Trang / Tiếng Gọi Làng Đoạn Hà] | Nhận một nhiệm vụ (tiến độ tự cập nhật khi chơi, hoàn thành tự trả thưởng) |

## /quy — Lệ quỷ và năng lực Ngự Quỷ Giả

| Lệnh | Tham số | Mô tả |
|---|---|---|
| `/quy ap_che` | — | Dán Bùa Áp Chế lên lệ quỷ của bạn (giảm 30 phục tô) |
| `/quy ban_giao` | — | Bàn giao Vật Chứa Vàng đã niêm phong cho kho Tổng Bộ để nhận thưởng |
| `/quy danh_sach` | — | Lệ quỷ bạn đang giữ, phục tô và cân bằng linh dị |
| `/quy nang_luc` | — | Dùng năng lực của lệ quỷ (làm phục tô tăng nhanh) |
| `/quy thong_tin` | `quy`* — [Quỷ Thủ / Quỷ Ảnh / Quỷ Nhãn / Quỷ Quan Tài / Quỷ Môn / Quỷ Vực] | Bách khoa lệ quỷ (mở dần theo manh mối bạn tìm được) |

## /su_kien — Sự kiện linh dị của thế giới

| Lệnh | Tham số | Mô tả |
|---|---|---|
| `/su_kien cau_chuyen` | — | Tiếp tục câu chuyện nhiều kết cục đang đọc dở (từ Thư Linh Dị) |
| `/su_kien danh_sach` | — | Sự kiện đang diễn ra |
| `/su_kien tham_gia` | `ma`* — Mã sự kiện (xem /su_kien danh_sach)<br>`hanh_dong`* — [Điều tra hiện trường / Áp chế linh dị / Sơ tán dân thường] | Đóng góp vào sự kiện tại địa điểm bạn đang đứng |

- `/tao_nhan_vat` — Tạo nhân vật và bắt đầu hành trình Ngự Quỷ Giả  
  Tham số: `ten`* — Tên nhân vật (2-24 ký tự)
- `/thanh_tuu` — Danh sách thành tựu
## /to_chuc — Tổng Bộ Linh Dị: tổ chức xử lý sự kiện linh dị

| Lệnh | Tham số | Mô tả |
|---|---|---|
| `/to_chuc bao_cao` | `noi_dung`* — 10-500 ký tự | Nộp báo cáo sự kiện (tối đa 3/ngày); cấp trên duyệt sẽ có thưởng |
| `/to_chuc duyet_bao_cao` | `ma` — Mã báo cáo; bỏ trống để xem danh sách<br>`duyet` — Đồng ý hay từ chối | (Người Phụ Trách trở lên) Xem và duyệt báo cáo |
| `/to_chuc gia_nhap` | — | Gia nhập Tổng Bộ với cấp Thành Viên |
| `/to_chuc giang_chuc` | `nguoi`* | Giáng một cấp cho người có cấp thấp hơn bạn |
| `/to_chuc giao_nhiem_vu` | `loai`* — [Khám phá / Tìm manh mối / Sống sót đối mặt / Phong ấn lệ quỷ]<br>`so_lan`* — 1-10<br>`thuong`* — Tiền cổ thưởng (trừ vào ngân quỹ)<br>`khu_vuc` — [Nội Thành / Ngoại Ô / Vùng Cấm]<br>`giao_cho` — Chỉ định một thành viên<br>`dia_diem` — [Khu Dân Cư Thanh Bình / Bệnh Viện Số Bảy / Trường Trung Học Minh Đức / Nghĩa Trang Bạch Vân / Làng Đoạn Hà / Phố Cổ Lục Môn / Ga Tàu Điện Cuối]<br>`quy` — [Quỷ Thủ / Quỷ Ảnh / Quỷ Nhãn / Quỷ Quan Tài / Quỷ Môn / Quỷ Vực]<br>`gio` — Hạn chót (giờ, 1-72) | (Đội Trưởng trở lên) Giao nhiệm vụ, thưởng lấy từ ngân quỹ |
| `/to_chuc ho_so_linh_di` | `quy` — Lệ quỷ cần đọc hồ sơ; bỏ trống để xem danh sách [Quỷ Thủ / Quỷ Ảnh / Quỷ Nhãn / Quỷ Quan Tài / Quỷ Môn / Quỷ Vực] | Hồ sơ linh dị: xem kho giam giữ hoặc đọc hồ sơ để nhận manh mối |
| `/to_chuc khu_vuc` | `nguoi`*<br>`khu_vuc`* — [Nội Thành / Ngoại Ô / Vùng Cấm] | Điều động thành viên sang khu vực khác |
| `/to_chuc loai` | `nguoi`* | Loại thành viên cấp thấp hơn khỏi Tổng Bộ |
| `/to_chuc mo_phong_toa` | `dia_diem`* — [Khu Dân Cư Thanh Bình / Bệnh Viện Số Bảy / Trường Trung Học Minh Đức / Nghĩa Trang Bạch Vân / Làng Đoạn Hà / Phố Cổ Lục Môn / Ga Tàu Điện Cuối] | (Người Phụ Trách trở lên) Tốn 150 ngân quỹ để tháo phong tỏa một khu |
| `/to_chuc nhan_nhiem_vu` | `ma`* | Nhận một nhiệm vụ tổ chức theo mã |
| `/to_chuc nhiem_vu` | — | Nhiệm vụ tổ chức dành cho bạn |
| `/to_chuc nop_quy` | `so_tien`* | Đóng góp tiền cổ vào ngân quỹ, nhận danh tiếng và cống hiến |
| `/to_chuc roi` | — | Rời Tổng Bộ |
| `/to_chuc thang_chuc` | `nguoi`*<br>`cap` — [Thành Viên / Đội Trưởng / Người Phụ Trách Khu Vực]<br>`khu_vuc` — [Nội Thành / Ngoại Ô / Vùng Cấm] | Thăng cấp cho thành viên (chỉ lên cấp thấp hơn cấp của bạn) |
| `/to_chuc thanh_vien` | — | Danh sách thành viên theo cấp bậc |
| `/to_chuc thong_tin` | — | Thông tin tổ chức, ngân quỹ, nhân sự |

- `/tro_giup` — Danh sách lệnh và cách chơi
- `/xoa_nhan_vat` — Xóa vĩnh viễn nhân vật và toàn bộ dữ liệu của bạn  
  Tham số: `xac_nhan`* — Gõ đúng tên nhân vật để xác nhận

Tổng cộng 58 lệnh.
