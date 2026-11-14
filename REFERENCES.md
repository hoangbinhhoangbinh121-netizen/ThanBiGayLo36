# Nguồn tham khảo và ranh giới thiết lập

## 1. Phạm vi nghiên cứu THỰC TẾ (ghi trung thực)

| Việc | Kết quả |
|---|---|
| Tìm kiếm tiếng Trung (4 lượt, các từ khóa trong danh sách yêu cầu: 驭鬼者, 厉鬼复苏, 灵异平衡, 总部, 黄金, 关押厉鬼, 鬼眼/鬼影/鬼手/鬼门...) | Có kết quả: bài cộng đồng, trang Qidian di động, Bilibili, Toutiao, trích đoạn chương trên 应用宝 |
| `https://m.xs8.cn/bookquery/clxaclnjyc` (bạn cung cấp) | **Đọc được.** Trang sách của Qidian/Yuewen: tác giả 佛前献花, 1618 chương, đã hoàn thành, ~5,32 triệu chữ; chương 1 nằm trong trang |
| `https://www.qidian.com/soushu/神秘复苏/` | **Bị từ chối** (`robots.txt` không cho truy cập tự động) |
| `https://www.baike.com/wikiid/3671844354670128071` | **Bị chặn** (chống bot) |
| `https://book.qidian.com/booklist/detail/647927/` | Chưa thử |
| Tài liệu Discord: `docs.discord.com/developers/resources/emoji` | **Đã đọc**, dùng để đối chiếu emoji ứng dụng |
| Tài liệu discord.py: ext.tasks (`change_interval`, công thức `before_loop` + `wait_until_ready`), mã nguồn discord.py 2.5.0 (có `fetch_application_emoji(s)`) | Đã đọc qua kết quả tìm kiếm |
| Mẫu `app_commands.Group` làm thuộc tính của Cog | Đối chiếu qua hướng dẫn Red-DiscordBot (xây trên discord.py) và ví dụ trong kho discord.py; **chưa đọc trang tham chiếu chính thức đầy đủ** |
| Pillow, SQLite, Python, Lospec, Piskel | **Chưa truy cập** |

Nghĩa là: nguyên tác được nghiên cứu ở mức **trích đoạn và bài tổng hợp**, chưa đọc trọn tiểu thuyết 1618 chương. Mã vẫn **chưa chạy với discord.py thật**. Mọi cơ chế cụ thể đều được đánh dấu là thiết lập riêng (mục 3).

## 2. Nguồn đã dùng

**Nguồn gốc (đọc trực tiếp):** trang sách xs8.cn ở trên. Chương 1 kể chuyện một học sinh lướt diễn đàn đọc bài "bác sĩ bệnh viện gặp xác ông lão tự đi ra khỏi nhà xác rồi tới gõ cửa nhà mình" (tiếng gõ, đèn phòng khách tắt, tiếng bước chân). Cảnh gõ cửa này là gốc của Quỷ Môn trong game; chữ trong tiểu thuyết **không** được sao chép.

**Bài cộng đồng / tổng hợp (không phải thiết lập chính thức; chỉ lấy ý lặp lại):**
- https://www.bilibili.com/opus/1138262759763345426 (cách chia mức C/B/A theo phạm vi gây hại và khả năng giam giữ)
- https://www.toutiao.com/zixun/7511954089979250738/ (tóm tắt quy luật: quỷ không giết được, chỉ né quy luật hoặc cách ly bằng vàng; dùng sức mạnh linh dị làm phục tô nhanh hơn; vật thế mạng do phòng thí nghiệm tổng bộ nghiên cứu; đinh quan tài vàng; quy luật "đi lẻ là chết" phải đi từ 3 người)
- https://www.toutiao.com/zixun/7526384351774099456/ (điểm danh các lệ quỷ hạng cao; mở đầu là quỷ gõ cửa: nghe tiếng gõ là chết, muốn sống thì đừng mở)
- https://www.toutiao.com/zixun/7483357858101282857/ (phân tích: quỷ ảnh, quỷ tay, đinh quan tài xuất hiện như công cụ của nhân vật chính)
- https://m.qidian.com/wenshu/qqbosrhos/ (hỏi đáp: càng gắn nhiều mắt quỷ và chồng nhiều tầng quỷ vực thì phục tô càng nhanh; quỷ vực duy trì được thời gian giới hạn)
- https://sj.qq.com/blog/2000000009213 (trích chương: nhân vật "người phụ trách" của một thành phố, thuộc lớp người đối phó lệ quỷ)
- Các trang đã xuất hiện ở đợt tìm kiếm đầu: bilibili.com/opus/1143089147677769750, m.qidian.com/chapter/1042070229/809888754/, m.qidian.com/chapter/1039635034/787766218 (tiêu đề chương nhắc "đinh quan tài") và vài trang Qidian khác; không chắc mọi trang đều là sách gốc.

## 3. Phân biệt: cảm hứng nguyên tác / suy luận / thiết lập riêng của game

**Ý tưởng cấu trúc lấy cảm hứng từ nguyên tác hoặc cộng đồng (độ chắc chắn: trung bình, chưa đối chiếu chương gốc):**
- Lệ quỷ giết người theo quy luật riêng; người sống sót thường nhờ hiểu quy luật hơn là sức mạnh.
- Người dùng sức mạnh của lệ quỷ thì lệ quỷ ấy dần phục tô; mất kiểm soát là rủi ro trung tâm.
- Phân cấp mức nguy hiểm kiểu C / B / A / S (cộng đồng; theo bài Bilibili, hạng phản ánh **phạm vi lan rộng/giam giữ được hay không**, không hẳn độ khó đối mặt; tên Việt do dự án đặt).
- Quỷ gõ cửa là lệ quỷ đầu tiên của truyện (quy luật gốc: nghe tiếng gõ là chết, đừng mở). Quỷ Môn trong game **đổi** thành quy luật chẵn/lẻ để thành bài toán suy luận.
- "Đi lẻ là chết, phải đi nhóm từ 3 người" → thưởng đội hình từ 3 người trong sự kiện địa điểm.
- Hồ sơ linh dị (灵异档案) và kho giam giữ (关押厉鬼) trong danh sách từ khóa của bạn → `Hồ sơ linh dị` của Tổng Bộ: bàn giao Vật Chứa Vàng thì mở hồ sơ, hồ sơ cho manh mối.
- Vật chứa bằng vàng dùng để cách ly/giam giữ linh dị.
- Có tổ chức tập trung xử lý sự kiện linh dị với tổng bộ và người phụ trách.
- "Vật thế mạng" và "đinh quan tài" gợi hứng từ các nhắc tới trong bài cộng đồng / tiêu đề chương; **cách vận hành trong game là tự thiết kế**.

**Thiết lập RIÊNG của game (không phải nguyên tác, không được coi là lore chính thức):**
- Toàn bộ 6 lệ quỷ (Quỷ Thủ, Quỷ Ảnh, Quỷ Nhãn, Quỷ Quan Tài, Quỷ Môn, Quỷ Vực): tên, nguồn gốc, quy luật cụ thể, quỷ vực, năng lực, manh mối.
- Vòng khắc chế thu→anh→nhan→mon→quan_tai→thu, cực tính động/tĩnh, cân bằng linh dị theo tổng cực tính, khuếch đại của Quỷ Vực.
- Công thức phục tô, khe chứa theo cấp, thức tỉnh sau 6 lần dùng khi còn ổn định, mất kiểm soát 15 phút.
- Địa danh (Hắc Thủy Thành, Làng Đoạn Hà, Phố Cổ Lục Môn...), vật phẩm, sự kiện, cốt truyện "Bức Thư Từ Người Đã Chết", cấp bậc và quyền hạn tổ chức, nhiệm vụ, thành tựu, kinh tế.
- Các tên tiếng Việt như "Quỷ Thủ" là bản dịch/đặt tên của dự án; dự án **không** tuyên bố chúng là tên nguyên tác.

## 4. Thuật ngữ trong danh sách yêu cầu (nguyên văn từ bạn, không do dự án suy diễn)

神秘复苏 Thần Bí Phục Tô · 灵异事件 sự kiện linh dị · 厉鬼 lệ quỷ · 鬼的规律 quy luật của quỷ · 杀人规律 quy luật giết người · 灵异力量 sức mạnh linh dị · 鬼域 quỷ vực · 驭鬼者 Ngự Quỷ Giả · 驾驭厉鬼 khống chế lệ quỷ · 厉鬼复苏 lệ quỷ phục tô · 灵异平衡 cân bằng linh dị · 失控 mất kiểm soát · 压制 áp chế · 关押厉鬼 giam giữ lệ quỷ · 灵异物品 vật phẩm linh dị · 黄金容器 vật chứa bằng vàng · 总部 tổng bộ · 负责人 người phụ trách · 规则怪谈 truyện quy tắc · 副本设计 thiết kế phó bản.

## 5. Bản quyền

- Không sao chép văn bản tiểu thuyết; mọi văn bản trong game do dự án tự viết.
- Không dùng hình nhân vật/tranh minh họa có bản quyền. 35 emoji PNG do `tools/generate_emoji.py` tự vẽ bằng Pillow (lưới 16×16, bảng màu tự chọn).
- Học hỏi cách xây dựng quy luật và bầu không khí kinh dị để tạo gameplay riêng.
