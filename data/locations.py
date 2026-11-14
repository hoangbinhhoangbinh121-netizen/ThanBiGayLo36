"""Địa điểm. Tên địa danh, sự cố, bảng rơi đồ là thiết lập riêng của game."""

HUB = "thanh_pho"

# incidents: (trọng số, văn bản, hiệu ứng) - hiệu ứng theo engine/effects.py
LOCATIONS = {
    "thanh_pho": {
        "name": "Hắc Thủy Thành - Khu Trung Tâm", "type": "thanh_pho", "emoji": "loc_thanh_pho", "region": "noi_thanh",
        "danger": 1, "safe": True, "shop": True, "hq": True,
        "desc": "Trung tâm thành phố, nơi đặt Tổng Bộ Linh Dị và những căn nhà an toàn dán kín vàng lá.",
        "links": ["khu_dan_cu", "benh_vien", "truong_hoc"], "ghosts": {}, "loot": {}, "coins": (0, 0), "incidents": [],
    },
    "khu_dan_cu": {
        "name": "Khu Dân Cư Thanh Bình", "type": "khu_dan_cu", "emoji": "loc_khu_dan_cu", "region": "noi_thanh",
        "danger": 3, "desc": "Dãy chung cư cũ, nhiều căn hộ bỏ trống. Có tiếng gõ cửa vào lúc không ai gõ.",
        "links": ["thanh_pho", "truong_hoc", "lang_hoang", "pho_co"],
        "ghosts": {"quy_mon": 5, "quy_anh": 2},
        "loot": {"den_dau": 4, "bang_gac": 4, "thuoc_an_than": 3, "thu_linh_di": 1}, "coins": (10, 35),
        "incidents": [
            (3, "Một người hàng xóm cười chào bạn rồi biến mất sau khúc quanh. Không ai ở tầng đó cả.", {"sanity": -5}),
            (3, "Bạn tìm thấy túi tiền cũ nhét dưới thảm chùi chân.", {"coins": 30}),
            (2, "Điện chập chờn rồi tắt hẳn trong 5 phút. Bạn đứng yên đếm từng giây.", {"sanity": -4, "corruption": 1}),
        ],
    },
    "benh_vien": {
        "name": "Bệnh Viện Số Bảy", "type": "benh_vien", "emoji": "loc_benh_vien", "region": "noi_thanh",
        "danger": 5, "desc": "Bệnh viện đóng cửa sau một vụ cháy. Giường bệnh vẫn còn ấm.",
        "links": ["thanh_pho", "nghia_trang"],
        "ghosts": {"quy_nhan": 4, "quy_thu": 3},
        "loot": {"bang_gac": 6, "thuoc_an_than": 3, "guong_nut": 1, "hinh_nhan": 1}, "coins": (15, 45),
        "incidents": [
            (3, "Máy đo nhịp tim bên cạnh bạn phát ra nhịp đập, nhịp của chính bạn nhưng chậm hơn một giây.", {"sanity": -7}),
            (2, "Bạn tìm thấy một tủ thuốc còn nguyên băng gạc.", {"items": {"bang_gac": 1}}),
            (2, "Có tiếng xe đẩy lăn ngoài hành lang. Khi bạn mở cửa, chỉ còn vệt bánh xe ướt.", {"hp": -6, "sanity": -3}),
        ],
    },
    "truong_hoc": {
        "name": "Trường Trung Học Minh Đức", "type": "truong_hoc", "emoji": "loc_truong_hoc", "region": "noi_thanh",
        "danger": 4, "desc": "Trường học bỏ hoang sau kỳ thi cuối cùng. Chuông vẫn reo mỗi đêm.",
        "links": ["thanh_pho", "khu_dan_cu"],
        "ghosts": {"quy_anh": 4, "quy_nhan": 2},
        "loot": {"den_dau": 5, "thuoc_an_than": 3, "thu_linh_di": 2}, "coins": (10, 30),
        "incidents": [
            (3, "Trên bảng đen có dòng chữ viết dở: 'Đừng đứng một mình dưới đèn.' Phấn còn ướt.", {"sanity": -3}),
            (3, "Bạn tìm thấy một chiếc cặp cũ, trong có ít tiền lẻ.", {"coins": 25}),
            (2, "Tiếng chuông reo giữa đêm. Bạn bịt tai suốt một phút.", {"sanity": -5}),
        ],
    },
    "nghia_trang": {
        "name": "Nghĩa Trang Bạch Vân", "type": "nghia_trang", "emoji": "loc_nghia_trang", "region": "ngoai_o",
        "danger": 6, "min_level": 2, "desc": "Mộ phần san sát, nhiều ngôi chôn thiếu người, nhiều ngôi chôn thừa.",
        "links": ["benh_vien", "lang_hoang"],
        "ghosts": {"quy_quan_tai": 5, "quy_thu": 2},
        "loot": {"quan_tai_nho": 1, "dinh_quan_tai": 1, "den_dau": 3, "thuoc_an_than": 3}, "coins": (20, 60),
        "incidents": [
            (3, "Một nén hương cháy ngược trước mộ vô danh. Bạn lùi lại nhưng nén hương vẫn hướng về phía bạn.", {"sanity": -6}),
            (2, "Dưới gốc cây khô có một hũ tiền cúng bị bỏ quên.", {"coins": 45}),
            (2, "Đất dưới chân lún xuống một nhịp. Bạn nhảy ra kịp lúc.", {"hp": -8}),
        ],
    },
    "lang_hoang": {
        "name": "Làng Đoạn Hà", "type": "lang_hoang", "emoji": "loc_lang_hoang", "region": "ngoai_o",
        "danger": 6, "min_level": 2, "desc": "Làng bỏ hoang bên con sông cạn. Mọi giếng đều có tiếng người gọi.",
        "links": ["nghia_trang", "khu_dan_cu"],
        "ghosts": {"quy_thu": 4, "quy_quan_tai": 2, "quy_mon": 2},
        "loot": {"quan_tai_nho": 1, "hinh_nhan": 1, "bang_gac": 3, "guong_nut": 1, "thu_linh_di": 1}, "coins": (20, 55),
        "incidents": [
            (3, "Tiếng gọi vọng từ đáy giếng đúng giọng người thân bạn. Bạn bước đi mà không quay đầu.", {"sanity": -8}),
            (2, "Trong một căn nhà sập, bạn nhặt được vài đồng tiền cổ.", {"coins": 40}),
            (2, "Dây thừng cũ quấn quanh cổ chân bạn rồi tự tuột ra.", {"hp": -7, "corruption": 1}),
        ],
    },
    "pho_co": {
        "name": "Phố Cổ Lục Môn", "type": "pho_co", "emoji": "ghost_quy_mon", "region": "vung_cam",
        "danger": 8, "min_level": 5, "requires_org": True, "sealed_zone": True,
        "desc": "Khu phố bị phong tỏa. Sáu cánh cổng, năm cánh đã bị hàn chết. Chỉ thành viên Tổng Bộ được qua chốt.",
        "links": ["khu_dan_cu"],
        "ghosts": {"quy_mon": 4, "quy_vuc": 3, "quy_anh": 2},
        "loot": {"vat_chua_vang": 2, "guong_nut": 2, "hinh_nhan": 2, "bua_ap_che": 3}, "coins": (40, 100),
        "incidents": [
            (3, "Cổng thứ sáu mở hé. Bạn thấy chính mình đứng bên trong, vẫy tay.", {"sanity": -12, "corruption": 2}),
            (2, "Dưới nền đá cũ có một chiếc hộp vàng bị lãng quên.", {"items": {"vat_chua_vang": 1}}),
        ],
    },
    "ga_cuoi": {
        "name": "Ga Tàu Điện Cuối", "type": "ga_cuoi", "emoji": "ghost_quy_vuc", "region": "vung_cam",
        "danger": 7, "min_level": 4, "requires_event": "chuyen_tau_cuoi",
        "desc": "Một nhà ga không có trên bản đồ. Chỉ xuất hiện khi chuyến tàu cuối đến.",
        "links": ["thanh_pho"],
        "ghosts": {"quy_vuc": 5, "quy_anh": 3},
        "loot": {"guong_nut": 2, "hinh_nhan": 2, "vat_chua_vang": 1, "thu_linh_di": 2}, "coins": (35, 90),
        "incidents": [
            (3, "Loa nhà ga đọc tên bạn kèm một giờ giấc chưa tới.", {"sanity": -9}),
            (2, "Trên ghế chờ có một ví da, bên trong đầy tiền cổ.", {"coins": 70}),
        ],
    },
}


def get(loc_id: str) -> dict:
    return LOCATIONS[loc_id]
