"""Dữ liệu cơ bản: xuất thân, vật phẩm, thành tựu, nhiệm vụ, cấp bậc tổ chức. Toàn bộ là thiết lập riêng của game."""

ORIGINS = {
    "hoc_sinh": {"name": "Học Sinh", "desc": "Trẻ, nhạy cảm với những điều lạ trong trường học.",
                 "max_hp": 95, "max_sanity": 110, "coins": 40, "items": {"den_dau": 1}},
    "y_ta": {"name": "Y Tá Ca Đêm", "desc": "Quen với xác chết và tiếng thở sau cánh cửa.",
             "max_hp": 110, "max_sanity": 100, "coins": 40, "items": {"bang_gac": 2}},
    "canh_sat": {"name": "Cảnh Sát Khu Vực", "desc": "Thể lực tốt, có chút tiền và đèn pin.",
                 "max_hp": 115, "max_sanity": 95, "coins": 60, "items": {"den_dau": 1}},
    "phong_vien": {"name": "Phóng Viên Điều Tra", "desc": "Hay hỏi, hay nghe, và hay giữ thư lạ.",
                   "max_hp": 100, "max_sanity": 100, "coins": 50, "items": {"thu_linh_di": 1}},
}

ITEM_CATS = {
    "linh_di_vat": "Linh Dị Vật", "phong_an": "Vật Phẩm Phong Ấn", "ho_tro": "Vật Phẩm Hỗ Trợ",
    "tieu_hao": "Vật Phẩm Tiêu Hao", "dac_biet": "Vật Phẩm Đặc Biệt",
}

# buy=None: không bán ở cửa hàng. sell: giá bán lại cho cửa hàng.
ITEMS = {
    "den_dau": {"name": "Đèn Dầu Cũ", "cat": "ho_tro", "emoji": "item_den_dau", "buy": 40, "sell": 15, "tradable": True,
                "desc": "Dùng trong đối mặt: Quỷ Ảnh (thắp đèn xua bóng). Hết dầu sau một lần."},
    "bang_gac": {"name": "Cuộn Băng Trắng", "cat": "tieu_hao", "emoji": "ui_sinh_ton", "buy": 25, "sell": 8, "tradable": True,
                 "use": {"hp": 30}, "desc": "Hồi 30 thể chất."},
    "thuoc_an_than": {"name": "Trà An Thần", "cat": "tieu_hao", "emoji": "ui_thanh_cong", "buy": 30, "sell": 10, "tradable": True,
                      "use": {"sanity": 30, "corruption": -3}, "desc": "Hồi 30 tinh thần, giảm 3 nhiễm linh dị."},
    "bua_ap_che": {"name": "Bùa Áp Chế", "cat": "phong_an", "emoji": "ui_phong_an", "buy": 80, "sell": 25, "tradable": True,
                   "desc": "Giảm 30 phục tô của một lệ quỷ (của mình hoặc của đồng đội đang mất kiểm soát). "
                           "Dán lên khung cửa trong đối mặt Quỷ Môn."},
    "vat_chua_vang": {"name": "Vật Chứa Vàng", "cat": "phong_an", "emoji": "item_vat_phong_an", "buy": 300, "sell": 90,
                      "tradable": True, "desc": "Vàng cách ly linh dị. Cần để phong ấn một lệ quỷ."},
    "dinh_quan_tai": {"name": "Đinh Quan Tài Vàng", "cat": "phong_an", "emoji": "item_quan_tai", "buy": None, "sell": 150,
                      "tradable": True, "desc": "Khóa chết nắp Quỷ Quan Tài; tăng khả năng khống chế nó."},
    "hinh_nhan": {"name": "Hình Nhân Thế Mạng", "cat": "dac_biet", "emoji": "item_hinh_nhan", "buy": 160, "sell": 50,
                  "tradable": True, "desc": "Tự động vỡ thay bạn khi chết (còn 1 thể chất). Cũng thế mạng cho Quỷ Thủ / Quỷ Quan Tài."},
    "thu_linh_di": {"name": "Thư Linh Dị", "cat": "dac_biet", "emoji": "item_thu_linh_di", "buy": None, "sell": 40,
                    "tradable": True, "desc": "Một bức thư không rõ người gửi. Đọc nó sẽ mở một câu chuyện nhiều kết cục."},
    "quan_tai_nho": {"name": "Quan Tài Nhỏ", "cat": "linh_di_vat", "emoji": "item_quan_tai", "buy": None, "sell": 120,
                     "tradable": True, "desc": "Linh dị vật. Đặt vào nắp Quỷ Quan Tài để nó nằm thay bạn."},
    "guong_nut": {"name": "Gương Nứt", "cat": "linh_di_vat", "emoji": "item_linh_di_vat", "buy": None, "sell": 100,
                  "tradable": True, "desc": "Linh dị vật. Phản chiếu ánh nhìn Quỷ Nhãn; soi ra neo của Quỷ Vực. Mỗi lần dùng tốn 5 tinh thần."},
}

ACHIEVEMENTS = {
    "buoc_dau": {"name": "Bước Đầu Trong Bóng Tối", "desc": "Khám phá lần đầu.", "stat": "explores", "target": 1, "reward": {"exp": 20}},
    "tho_manh_moi": {"name": "Thợ Săn Manh Mối", "desc": "Tìm 10 manh mối.", "stat": "clues", "target": 10, "reward": {"rep": 3, "coins": 50}},
    "song_sot": {"name": "Kẻ Sống Sót", "desc": "Sống sót 5 lần đối mặt lệ quỷ.", "stat": "survives", "target": 5, "reward": {"rep": 4, "exp": 100}},
    "phong_an_su": {"name": "Phong Ấn Sư", "desc": "Phong ấn 3 lệ quỷ.", "stat": "seals", "target": 3, "reward": {"rep": 10, "coins": 300}},
    "ngu_quy_gia": {"name": "Ngự Quỷ Giả", "desc": "Khống chế lệ quỷ đầu tiên.", "stat": "binds", "target": 1, "reward": {"rep": 5, "exp": 100}},
    "chet_mot_lan": {"name": "Đã Chết Một Lần", "desc": "Chết lần đầu.", "stat": "deaths", "target": 1, "reward": {"exp": 10}},
    "mat_kiem_soat": {"name": "Rìa Vực Thẳm", "desc": "Mất kiểm soát lần đầu.", "stat": "lost_control", "target": 1, "reward": {"exp": 20}},
    "thuc_tinh": {"name": "Thức Tỉnh", "desc": "Thức tỉnh năng lực lệ quỷ.", "stat": "awakens", "target": 1, "reward": {"rep": 8, "exp": 150}},
    "chien_su_kien": {"name": "Người Của Hiện Trường", "desc": "Tham gia 3 sự kiện.", "stat": "events", "target": 3, "reward": {"rep": 4, "coins": 80}},
    "thuong_nhan": {"name": "Thương Nhân Bóng Đêm", "desc": "Hoàn tất 3 giao dịch.", "stat": "trades", "target": 3, "reward": {"coins": 60}},
    "bao_cao_vien": {"name": "Cây Bút Của Tổng Bộ", "desc": "Có 3 báo cáo được duyệt.", "stat": "reports", "target": 3, "reward": {"rep": 6}},
}

# Mục tiêu: type in explore|clue|loot|survive|seal|bind|event|report ; ghost/loc/item tùy chọn
QUESTS = {
    "q_dieu_tra": {"name": "Điều Tra Lần Đầu", "desc": "Khám phá 3 lần ở bất kỳ nơi nào.", "min_level": 1,
                   "obj": {"type": "explore", "n": 3}, "reward": {"coins": 60, "exp": 40, "items": {"den_dau": 1}}},
    "q_manh_moi": {"name": "Thu Thập Manh Mối", "desc": "Tìm 3 manh mối bất kỳ.", "min_level": 1,
                   "obj": {"type": "clue", "n": 3}, "reward": {"rep": 3, "exp": 60, "items": {"thuoc_an_than": 1}}},
    "q_song_sot": {"name": "Sống Sót", "desc": "Sống sót qua 2 lần đối mặt lệ quỷ.", "min_level": 2,
                   "obj": {"type": "survive", "n": 2}, "reward": {"coins": 100, "items": {"hinh_nhan": 1}}},
    "q_phong_an": {"name": "Phong Ấn Đầu Tiên", "desc": "Phong ấn một lệ quỷ.", "min_level": 3,
                   "obj": {"type": "seal", "n": 1}, "reward": {"rep": 10, "exp": 200, "coins": 200}},
    "q_ngu_quy": {"name": "Con Đường Ngự Quỷ", "desc": "Khống chế một lệ quỷ.", "min_level": 3,
                  "obj": {"type": "bind", "n": 1}, "reward": {"rep": 5, "exp": 150}},
    "q_nghia_trang": {"name": "Hồ Sơ Nghĩa Trang", "desc": "Tìm 2 manh mối về Quỷ Quan Tài.", "min_level": 2,
                      "obj": {"type": "clue", "n": 2, "ghost": "quy_quan_tai"}, "reward": {"items": {"dinh_quan_tai": 1}, "exp": 80}},
    "q_lang_hoang": {"name": "Tiếng Gọi Làng Đoạn Hà", "desc": "Khám phá Làng Đoạn Hà 2 lần.", "min_level": 3,
                     "obj": {"type": "explore", "n": 2, "loc": "lang_hoang"}, "reward": {"items": {"quan_tai_nho": 1}, "rep": 2}},
}

# Cấp bậc tổ chức: (giá trị, tên, danh tiếng tối thiểu để được thăng vào cấp này)
RANKS = {
    "thanh_vien": (1, "Thành Viên", 0),
    "doi_truong": (2, "Đội Trưởng", 20),
    "phu_trach": (3, "Người Phụ Trách Khu Vực", 60),
    "tong_bo": (4, "Tổng Bộ", 150),
}
REGIONS = {"noi_thanh": "Nội Thành", "ngoai_o": "Ngoại Ô", "vung_cam": "Vùng Cấm"}
MISSION_TYPES = {"explore": "Khám phá", "clue": "Tìm manh mối", "survive": "Sống sót đối mặt", "seal": "Phong ấn lệ quỷ"}
