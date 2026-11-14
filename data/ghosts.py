"""Dữ liệu lệ quỷ.

NGUỒN GỐC THIẾT LẬP:
- Phân cấp C/B/A/S theo mức lan rộng: tham khảo cộng đồng (xem REFERENCES.md), KHÔNG phải tài liệu chính thức.
- Quỷ Môn lấy cảm hứng từ lệ quỷ gõ cửa mở đầu truyện; quy luật chẵn/lẻ là thiết kế riêng.
- Nguyên lý "quỷ không giết được, chỉ né quy luật / vật chứa vàng / quỷ chế quỷ / phục tô khi dùng": tham khảo nguyên tác.
- TOÀN BỘ tên quỷ, quy luật cụ thể, năng lực, vòng khắc chế, cực tính, manh mối bên dưới là THIẾT LẬP RIÊNG CỦA GAME.
"""

RANK_LEVEL = {"C": 1, "B": 2, "A": 4, "S": 8}
RANK_NAME = {"C": "Hạn chế (C)", "B": "Nguy hiểm (B)", "A": "Tai ương (A)", "S": "Tai họa (S)"}
BIND_BASE = {"C": 0.70, "B": 0.50, "A": 0.30, "S": 0.12}

# Năng lực: out = hiệu ứng ngoài đối mặt; enc = hiệu ứng khi đang đối mặt (None = không dùng được)
GHOSTS = {
    "quy_thu": {
        "name": "Quỷ Thủ", "emoji": "ghost_quy_thu", "rank": "B", "mechanic": "quy_thu",
        "origin": "Một người bị kéo xuống giếng cạn ở Làng Đoạn Hà, kêu cứu suốt đêm mà không ai nắm lấy tay họ. "
                  "Bàn tay ấy vẫn đi tìm một cổ chân để níu lại.",
        "kill_rule": "Nó chỉ siết chặt kẻ chống cự. Giãy giụa thì nó siết thêm; đứng yên, nó nới ra.",
        "range": "Trong tầm một cánh tay, nhưng tay có thể mọc ra từ bất kỳ khe tối nào.",
        "domain": {"name": "Gầm Tối", "desc": "Khoảng tối dưới mọi vật có gầm: giường, bàn, xe.",
                   "entry": {"sanity": -3}},
        "counter": "Giữ bất động và im lặng; đưa vật thế mạng để nó nắm thay.",
        "suppress_text": "Bị khắc chế bởi Quỷ Quan Tài (quan tài giam được bàn tay).",
        "rate": 2.0, "use_cost": 8, "polarity": 2,
        "suppresses": ["quy_anh"], "conflicts": ["quy_mon"],
        "clues": [
            "Vết bầm xanh hình bàn tay quanh cổ chân càng sâu ở những nạn nhân càng vùng vẫy.",
            "Người sống sót đều nói cùng một câu: 'Tôi đứng yên cho đến khi nó chán.'",
            "Nó từng nới tay khi bị dúi vào một hình nhân giấy mang tên người sống.",
        ],
        "powers": [{"id": "nam_lay", "name": "Nắm Lấy", "cost": 8, "corr": 2,
                    "desc": "Bàn tay quỷ lục lọi giúp bạn: 2 lần Tìm đồ kế tiếp được thêm một lượt nhặt (thức tỉnh: 4 lần). "
                            "Khi đối mặt: giữ tay kia lại, tiến triển thêm một nhịp.",
                    "out": "loot", "enc": "progress"}],
        "awaken": "Thức tỉnh: Bàn tay chịu nghe lời, năng lực mạnh gấp đôi và tốn ít phục tô hơn.",
        "resurrect_text": "Bàn tay phình to, xé toạc ống tay áo chủ nhân và kéo cả người xuống bóng tối.",
    },
    "quy_anh": {
        "name": "Quỷ Ảnh", "emoji": "ghost_quy_anh", "rank": "C", "mechanic": "quy_anh",
        "origin": "Bóng của một học sinh bị bỏ quên trong phòng học tắt đèn suốt một học kỳ. Nó học được cách đứng thế chỗ bóng của người khác.",
        "kill_rule": "Nó chỉ dẫm lên bóng của kẻ đứng dưới đúng MỘT nguồn sáng. Hai đèn hay bóng tối hoàn toàn thì nó không với tới.",
        "range": "Mọi nơi có ánh sáng và vật cản; mạnh nhất trong hành lang và phòng học.",
        "domain": {"name": "Hành Lang Bóng", "desc": "Hành lang kéo dài vô tận, đèn chập chờn.",
                   "entry": {"sanity": -3}},
        "counter": "Tránh chỗ có đúng một ngọn đèn; đứng nơi tối hẳn hoặc nhiều ánh sáng.",
        "suppress_text": "Bị khắc chế bởi Quỷ Thủ (tay túm được bóng).",
        "rate": 1.5, "use_cost": 10, "polarity": -1,
        "suppresses": ["quy_nhan"], "conflicts": ["quy_quan_tai"],
        "clues": [
            "Mọi vết cháy sém trên sàn nằm đúng dưới những ngọn đèn đơn lẻ, không bao giờ dưới hai đèn hay trong bóng tối hoàn toàn.",
            "Bóng người thứ hai trong ảnh chụp luôn đứng ở nơi chỉ có một nguồn sáng.",
            "Những người sống sót đều đứng ở nơi tối hẳn hoặc giữa nhiều ánh sáng.",
        ],
        "powers": [{"id": "an_than", "name": "Ẩn Bóng", "cost": 10, "corr": 3,
                    "desc": "Giấu bóng mình: lần đối mặt kế tiếp bắt đầu với 1 lớp khiên (thức tỉnh: 2). "
                            "Khi đối mặt: thêm một lớp khiên chặn đòn.",
                    "out": "shadow", "enc": "shield"}],
        "awaken": "Thức tỉnh: Bóng tách ra thành thân phận thứ hai, khiên dày gấp đôi.",
        "resurrect_text": "Bóng dưới chân chủ nhân đứng dậy, bước đi một mình, và kéo theo thân xác.",
    },
    "quy_nhan": {
        "name": "Quỷ Nhãn", "emoji": "ghost_quy_nhan", "rank": "B", "mechanic": "quy_nhan",
        "origin": "Con mắt của một người gác đêm bệnh viện, mở trừng khi thấy thứ không nên thấy và không bao giờ nhắm lại.",
        "kill_rule": "Ai nhìn thẳng vào nó quá ba nhịp sẽ không rời mắt được nữa. Nhắm mắt thì nó tiến lại gần.",
        "range": "Mọi thứ trong tầm nhìn của nó, kể cả qua gương và kính.",
        "domain": {"name": "Phòng Bệnh Không Đáy", "desc": "Dãy phòng bệnh mà mọi cánh cửa đều có ô kính nhìn vào bạn.",
                   "entry": {"sanity": -4}},
        "counter": "Nhìn rồi nhắm mắt luân phiên; dùng gương nứt đẩy ánh nhìn của nó đi.",
        "suppress_text": "Bị khắc chế bởi Quỷ Ảnh (bóng che mắt).",
        "rate": 2.5, "use_cost": 12, "polarity": -2,
        "suppresses": ["quy_mon"], "conflicts": ["quy_vuc"],
        "clues": [
            "Hồ sơ ghi: ai nhìn thẳng vào nó quá ba nhịp thì ánh mắt không rời ra được nữa.",
            "Nhắm mắt làm nó tiến lại gần, nhưng đồng thời xóa dấu ấn đã in lên người.",
            "Gương vỡ phản chiếu ánh nhìn của nó lại, đẩy nó lùi ra xa.",
        ],
        "powers": [{"id": "xuyen_thau", "name": "Xuyên Thấu", "cost": 12, "corr": 3,
                    "desc": "Con mắt nhìn xuyên: Điều tra manh mối kế tiếp chắc chắn ra manh mối. "
                            "Khi đối mặt: thấy trọn mọi quy luật đã biết.",
                    "out": "sight", "enc": "reveal"}],
        "awaken": "Thức tỉnh: Con mắt thứ hai mở, nhìn thấu cả nơi chưa từng đặt chân tới.",
        "resurrect_text": "Mắt trên tay chủ nhân mở ra, và cả căn phòng bắt đầu nhìn lại.",
    },
    "quy_quan_tai": {
        "name": "Quỷ Quan Tài", "emoji": "ghost_quy_quan_tai", "rank": "B", "mechanic": "quy_quan_tai",
        "origin": "Cỗ quan tài chôn thiếu người ở Nghĩa Trang Bạch Vân; nắp quan tài không đóng nổi và luôn mời gọi kẻ mệt mỏi.",
        "kill_rule": "Nó mời người ta nằm vào. Ai nằm xuống sẽ không bao giờ dậy. Nắp chỉ chịu đóng khi trong đó đã có thứ nằm thay.",
        "range": "Quanh cỗ quan tài; giọng mời vang xa hơn khi người nghe càng kiệt sức.",
        "domain": {"name": "Linh Đường Vắng", "desc": "Gian linh đường chỉ có một cỗ quan tài mở nắp và hàng nến cháy ngược.",
                   "entry": {"sanity": -3, "corruption": 2}},
        "counter": "Giữ ý chí, đóng nắp từng chút; hoặc cho nó thứ nằm thay (Hình Nhân, Quan Tài Nhỏ); đinh vàng khóa chết nắp.",
        "suppress_text": "Bị khắc chế bởi Quỷ Môn (cánh cửa chặn nắp).",
        "rate": 2.0, "use_cost": 15, "polarity": -1,
        "suppresses": ["quy_thu"], "conflicts": ["quy_anh"],
        "clues": [
            "Nắp quan tài chỉ chịu đóng khi trong đó đã có thứ nằm vào.",
            "Giọng mời mạnh dần theo từng lần ý chí suy yếu; người còn tỉnh táo mới đóng nổi nắp.",
            "Đinh vàng đóng xuống nắp làm giọng nói tắt hẳn.",
        ],
        "powers": [{"id": "dong_nap", "name": "Đóng Nắp", "cost": 15, "corr": 4,
                    "desc": "Giam bớt linh dị: giảm 35 phục tô của một lệ quỷ khác bạn đang giữ (thức tỉnh: 60). "
                            "Khi đối mặt: thêm một lớp khiên.",
                    "out": "suppress", "enc": "shield"}],
        "awaken": "Thức tỉnh: Nắp quan tài tự khép lại cho chủ nhân, áp chế mạnh gấp đôi.",
        "resurrect_text": "Nắp quan tài mở toang giữa lòng phố. Chủ nhân là kẻ đầu tiên được mời nằm vào.",
    },
    "quy_mon": {
        "name": "Quỷ Môn", "emoji": "ghost_quy_mon", "rank": "C", "mechanic": "quy_mon",
        "origin": "Cánh cửa căn hộ số 7 Khu Thanh Bình, nơi cô con gái bị nhốt rồi quên lãng gõ cửa suốt mười năm.",
        "kill_rule": "Tiếng gõ LẺ là của nó: mở cửa là mất tích. Tiếng gõ CHẴN là người sống cầu cứu.",
        "range": "Mọi cánh cửa mà tiếng gõ vọng tới được.",
        "domain": {"name": "Hành Lang Cửa Đóng", "desc": "Dãy cửa giống hệt nhau kéo dài, mỗi cánh đều có người đang gõ.",
                   "entry": {"sanity": -2}},
        "counter": "Phân biệt chẵn/lẻ; im lặng với tiếng lẻ; dán bùa lên khung cửa.",
        "suppress_text": "Bị khắc chế bởi Quỷ Nhãn (mắt nhìn xuyên cửa).",
        "rate": 1.5, "use_cost": 10, "polarity": 1,
        "suppresses": ["quy_quan_tai"], "conflicts": ["quy_thu"],
        "clues": [
            "Tiếng gõ lẻ là của nó; tiếng gõ chẵn là của người sống cầu cứu.",
            "Mở cửa khi gõ lẻ thì không ai thấy người mở nữa; im lặng với gõ chẵn thì chỉ mất một lời cầu cứu.",
            "Bùa dán lên khung cửa làm tiếng gõ ngừng hẳn.",
        ],
        "powers": [{"id": "mo_cua", "name": "Mở Cửa", "cost": 10, "corr": 3,
                    "desc": "Mở cánh cửa tới nơi an toàn: lập tức về Khu Trung Tâm từ bất cứ đâu (không dùng khi đang đối mặt). "
                            "Khi đối mặt: thoát khỏi cuộc đối mặt ngay.",
                    "out": "teleport", "enc": "escape"}],
        "awaken": "Thức tỉnh: Cánh cửa mở được tới bất kỳ nơi đã từng đặt chân, ít tốn phục tô hơn.",
        "resurrect_text": "Mọi cánh cửa quanh chủ nhân đồng loạt mở ra, và tiếng gõ vọng từ bên trong.",
    },
    "quy_vuc": {
        "name": "Quỷ Vực", "emoji": "ghost_quy_vuc", "rank": "A", "mechanic": "quy_vuc",
        "origin": "Không phải một thực thể mà là một vùng: chỗ một đoàn tàu đêm biến mất cùng toàn bộ hành khách. "
                  "Nó có một 'neo' giữ vùng ấy lại.",
        "kill_rule": "Không khí trong vực cạn dần theo từng hành động. Hết không khí là hết người. Phá đúng neo thì vực sụp.",
        "range": "Một vùng lan rộng theo nhịp, không có hình thể.",
        "domain": {"name": "Chính Nó", "desc": "Bản thân quỷ là vực: bước vào là ở trong, không lối ra.",
                   "entry": {"sanity": -6, "corruption": 3}},
        "counter": "Thăm dò để tìm neo, phá neo; gương nứt soi ra vị trí neo.",
        "suppress_text": "Không bị quỷ nào khắc chế, nhưng khuếch đại mọi lệ quỷ khác bạn giữ (+30% tốc độ phục tô).",
        "rate": 3.5, "use_cost": 25, "polarity": 0,
        "suppresses": [], "conflicts": ["quy_nhan"],
        "clues": [
            "Hơi lạnh trong quỷ vực dồn về một trục nhất định, nơi 'neo' của nó nằm.",
            "Thăm dò càng gần neo, hơi lạnh càng đặc quánh; phía đối diện lại yên tĩnh lạ thường.",
            "Phá đúng neo thì quỷ vực sụp xuống; phá sai chỉ làm nó siết nhanh hơn.",
        ],
        "powers": [{"id": "mo_vuc", "name": "Mở Vực", "cost": 25, "corr": 6,
                    "desc": "Trải quỷ vực quanh mình: 3 lần Khám phá kế tiếp giảm mạnh nguy hiểm và gặp quỷ (thức tỉnh: 5 lần). "
                            "Khi đối mặt: thêm một lớp khiên và thấy trọn quy luật đã biết.",
                    "out": "domain", "enc": "shield_reveal"}],
        "awaken": "Thức tỉnh: Quỷ vực nghe theo chủ nhân, kéo dài lâu hơn và ít tốn phục tô hơn.",
        "resurrect_text": "Quỷ vực bung ra nuốt cả khu phố; không ai còn nhớ ranh giới giữa hai bên.",
    },
}

# Khắc chế vòng: thu→anh→nhan→mon→quan_tai→thu. Quỷ Vực khuếch đại mọi quỷ khác.
HUB_GHOST_NONE = None


def ghost_name(ghost_id: str) -> str:
    return GHOSTS[ghost_id]["name"]


def suppressors_of(ghost_id: str) -> list[str]:
    return [gid for gid, g in GHOSTS.items() if ghost_id in g["suppresses"]]
