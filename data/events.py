"""Sự kiện thế giới và cốt truyện nhiều kết cục. Thiết lập riêng của game.

kind:
  contrib - sự kiện có địa điểm: người chơi cùng đóng góp để đạt `goal` trước hạn.
  global  - sự kiện toàn máy chủ: thay đổi hệ số cho cả thế giới trong một khoảng thời gian.
  timed   - sự kiện giới hạn thời gian: mở một lối đi tạm thời.
"""

CONTRIB_ACTIONS = {
    "dieu_tra": {"name": "Điều tra hiện trường", "desc": "Tốn 5 tinh thần. +2 đóng góp.", "contrib": 2, "sanity": -5},
    "ap_che": {"name": "Áp chế linh dị", "desc": "Dùng lệ quỷ đang giữ (+12 phục tô) hoặc 1 Bùa Áp Chế. +4 đóng góp.", "contrib": 4},
    "so_tan": {"name": "Sơ tán dân thường", "desc": "Tốn 5 thể chất. +2 đóng góp, +1 danh tiếng.", "contrib": 2, "hp": -5, "rep": 1},
}

EVENT_DEFS = {
    "phuc_to": {
        "kind": "contrib", "title": "Lệ Quỷ Phục Tô", "spawn_ghost": False, "weight": 0,  # chỉ do phục tô thật kích hoạt
        "duration": 5400, "goal": 12, "reward_mult": 1.5, "fail_lock": 7200,
        "desc": "Một lệ quỷ vừa phục tô. Mỗi phút trôi qua, vùng linh dị lan rộng thêm.",
    },
    "quy_xuat_hien": {
        "kind": "contrib", "title": "Quỷ Xuất Hiện", "spawn_ghost": True, "weight": 6,
        "duration": 3600, "goal": 10, "reward_mult": 1.0, "fail_lock": 7200,
        "desc": "Có người báo thấy bóng dáng không nên có. Cần người điều tra và áp chế trước khi nó đứng vững.",
    },
    "khan_cap": {
        "kind": "contrib", "title": "Nhiệm Vụ Khẩn Cấp", "spawn_ghost": False, "weight": 3,
        "duration": 2400, "goal": 8, "reward_mult": 1.5, "fail_lock": 3600,
        "desc": "Tổng Bộ phát lệnh khẩn: khu vực xuất hiện dấu hiệu linh dị bất thường, cần tay chân tới hiện trường.",
    },
    "dem_trang_mau": {
        "kind": "global", "title": "Đêm Trăng Máu", "weight": 2, "duration": 7200,
        "mods": {"danger_add": 1, "clue_bonus": 0.15, "encounter_add": 5},
        "desc": "Trăng đỏ như máu. Linh dị trỗi dậy khắp nơi, nhưng manh mối cũng dễ lộ ra hơn.",
    },
    "suong_mu": {
        "kind": "global", "title": "Sương Mù Dày Đặc", "weight": 2, "duration": 5400,
        "mods": {"loot_mult": 1.5, "encounter_add": 8},
        "desc": "Sương trắng phủ kín thành phố. Dễ nhặt được đồ bị bỏ quên, nhưng cũng dễ đụng phải thứ trong sương.",
    },
    "chuyen_tau_cuoi": {
        "kind": "timed", "title": "Chuyến Tàu Cuối", "weight": 2, "duration": 3600, "unlocks": "ga_cuoi",
        "desc": "Một đoàn tàu không có trong lịch trình đang vào ga. Ga Tàu Điện Cuối mở cửa trong một giờ. "
                "Kẻ nào còn ở đó khi tàu rời đi sẽ bị đưa về trong tình trạng tồi tệ.",
        "expire_penalty": {"sanity": -30, "corruption": 10},
    },
}

# Cốt truyện nhiều kết cục. Mỗi lựa chọn có thể có: req_loc, req_item, req_org, fx (hiệu ứng), goto | end
STORIES = {
    "buc_thu": {
        "title": "Bức Thư Từ Người Đã Chết",
        "start": "mo_dau",
        "nodes": {
            "mo_dau": {
                "text": "Bạn mở Thư Linh Dị. Nét chữ run rẩy, mực còn ướt: 'Xin đừng để tôi một mình ở đây.' "
                        "Dưới cùng là một địa chỉ: căn hộ số 7, Khu Dân Cư Thanh Bình.",
                "choices": [
                    {"id": "doc_tiep", "label": "Đọc tiếp", "goto": "phong_khoa"},
                    {"id": "dot_thu", "label": "Đốt bức thư", "end": "dot_thu"},
                ],
            },
            "phong_khoa": {
                "text": "Lá thư kể về một căn phòng bị khóa từ bên ngoài. Người viết là cô con gái đã chết hơn mười năm. "
                        "Dòng cuối: 'Mở cửa giúp tôi. Hoặc đừng mở, và đừng quên tôi.'",
                "choices": [
                    {"id": "mo_cua", "label": "Mang thư tới căn hộ số 7 mở cửa (cần đang ở Khu Dân Cư)", "req_loc": "khu_dan_cu", "end": "mo_cua"},
                    {"id": "bao_tong_bo", "label": "Giao thư cho Tổng Bộ (cần là thành viên Tổng Bộ)", "req_org": True, "end": "bao_tong_bo"},
                    {"id": "viet_thu", "label": "Thắp đèn dầu viết thư trả lời (cần Đèn Dầu Cũ)", "req_item": "den_dau", "end": "viet_thu"},
                ],
            },
        },
        "endings": {
            "dot_thu": {
                "text": "Ngọn lửa liếm hết nét chữ. Lá thư cháy ngược, rồi tắt. Bạn hơi buồn mà không hiểu vì sao.",
                "fx": {"sanity": -3, "rep": 1, "world": {"unrest": -2}},
            },
            "mo_cua": {
                "text": "Cánh cửa bật mở, bên trong chỉ có một chiếc ghế và tiếng thở. Thứ gì đó theo bạn ra ngoài. "
                        "Bạn biết thêm một điều về nó, và khu chung cư không còn như cũ.",
                "fx": {"corruption": 10, "exp": 80, "clues": [["quy_mon", 1]],
                       "world": {"danger_mod": {"khu_dan_cu": 1}, "spawn_ghost": {"loc": "khu_dan_cu", "ghost": "quy_mon"}}},
            },
            "bao_tong_bo": {
                "text": "Tổng Bộ niêm phong căn hộ số 7 và cử người canh gác. Khu chung cư bị phong tỏa nửa giờ, "
                        "nhưng thêm một oan hồn được yên nghỉ. Bạn nhận được ghi nhận xứng đáng.",
                "fx": {"rep": 5, "coins": 60, "world": {"unrest": -3, "lock": {"khu_dan_cu": 1800}}},
            },
            "viet_thu": {
                "text": "Ánh đèn dầu soi ra nét chữ thứ hai bên dưới: 'Cảm ơn.' Trên bàn xuất hiện một mảnh gương nứt. "
                        "Căn hộ số 7 từ đó chỉ còn tiếng gõ nhẹ vào ban đêm.",
                "fx": {"sanity": 5, "exp": 60, "items": {"guong_nut": 1}, "clues": [["quy_mon", 2]], "world": {"unrest": -1}},
                "consume": {"den_dau": 1},
            },
        },
    },
}

STORY_BY_ITEM = {"thu_linh_di": "buc_thu"}
