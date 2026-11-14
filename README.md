# Thần Bí Phục Tô — Discord MMORPG  ·  *Bot By Tuyệt Thiên*

Bot Discord MMORPG kinh dị linh dị lấy cảm hứng từ 《神秘复苏》. Người chơi là **Ngự Quỷ Giả**: khám phá nơi bị lệ quỷ chiếm, tìm manh mối để sống sót trước quy luật giết người của từng con quỷ, khống chế hoặc phong ấn chúng, và cân bằng cái giá phải trả: lệ quỷ trong người luôn **phục tô** dần.

> Đọc `REFERENCES.md` trước: nó ghi rõ phần nào là cảm hứng nguyên tác, phần nào là thiết lập riêng của game, và nghiên cứu nguyên tác đã làm nông tới mức nào. Đọc `TEST_REPORT.md` để biết cái gì đã/chưa được kiểm thử.

## Có gì bên trong
- 6 lệ quỷ, mỗi con một cơ chế đối mặt riêng (không phải một bộ chỉ số đổi tên) · khắc chế vòng · cân bằng linh dị · phục tô · thức tỉnh · phong ấn
- 8 địa điểm, phong tỏa, nguy hiểm động · khám phá / điều tra manh mối / sự cố / đối mặt
- Sự kiện: phục tô, quỷ xuất hiện, khẩn cấp, toàn máy chủ, giới hạn thời gian, cốt truyện nhiều kết cục · nhiệm vụ · thành tựu
- Tổng Bộ: 4 cấp quyền hạn, nhiệm vụ tổ chức (ký quỹ), báo cáo sự kiện, mở phong tỏa, xếp hạng, **Hồ sơ linh dị** (kho giam giữ + manh mối dùng chung)
- Vật phẩm, cửa hàng, giao dịch nguyên tử giữa người chơi
- 35 emoji pixel art PNG tự vẽ, tích hợp trong Embed, Select Menu, Nút
- SQLite có migration (5 bản), sao lưu nóng định kỳ, log xoay vòng ra file, chống spam, kiểm tra quyền, xóa nhân vật an toàn, xử lý lỗi, 95 test, mô phỏng cân bằng

## Cấu trúc
```
bot.py                 điểm khởi động (TBPTBot)
core/                  database (migration, backup), config, emoji, render (Embed), guards, cooldown, bus
engine/                LOGIC THUẦN, không phụ thuộc Discord (players, ghosts, mechanics, encounters, world,
                       events, economy, orgs, progress, game)
data/                  dữ liệu: ghosts, locations, events, basics (vật phẩm, nhiệm vụ, thành tựu, cấp bậc)
cogs/                  8 Cog: character, world, explore, ghosts, items, org, events, admin
migrations/            001..005 .sql (áp tự động khi khởi động)
assets/emoji/          PNG theo nhóm + emoji_map.json + _contact_sheet.png
tools/                 generate_emoji.py, init_db.py, gen_docs.py, balance_sim.py
tests/                 95 test (+ fake_discord.py: giả lập discord để kiểm thử ngoại tuyến)
storage/               cơ sở dữ liệu SQLite (kèm bản rỗng đã khởi tạo)     backups/  bản sao lưu
docs/                  GAME_DESIGN.md, DATABASE.md, BALANCE.md
```
Mọi lệnh Discord đều mỏng: gọi `engine/*` (có logic thật, có test) rồi dựng Embed. Không có lệnh nào chỉ có giao diện.

## Cài đặt
Yêu cầu: **Python ≥ 3.10**.

1. Giải nén, vào thư mục dự án, tạo môi trường ảo (khuyến nghị):
   `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
2. `pip install -r requirements.txt` (cần `discord.py >= 2.5` cho emoji ứng dụng)
3. Tạo bot tại https://discord.com/developers/applications → *Bot* → copy **token**. Không cần bật Privileged Intents (bot chỉ dùng lệnh slash).
4. Mời bot: OAuth2 → URL Generator → scope `bot` + `applications.commands`; quyền `Send Messages`, `Embed Links`, `Use Application Commands`.
5. Cấu hình: `cp config.example.json config.json`, điền `owner_ids` (ID Discord của bạn). Đặt token bằng biến môi trường (an toàn hơn ghi vào file):
   `export DISCORD_TOKEN="..."` (Windows PowerShell: `$env:DISCORD_TOKEN="..."`).
   Khi thử nghiệm nên đặt `guild_id` là ID máy chủ test để lệnh xuất hiện tức thì (lệnh toàn cục có thể mất tới ~1 giờ).
6. Chạy: `python bot.py`. Lần đầu bot tự: tạo/ nâng cấp DB, **tải 35 emoji lên làm emoji ứng dụng**, nạp Cog, đồng bộ lệnh.
7. Thiết lập trong Discord: `/admin kenh #kênh` (kênh nhận thông báo sự kiện), `/admin bo_nhiem @bạn` (Tổng Bộ đầu tiên), người chơi dùng `/tao_nhan_vat`.

Nếu tải emoji lỗi (thư viện cũ, thiếu quyền), bot vẫn chạy và dùng ký tự dự phòng tạm thời; sửa nguyên nhân rồi dùng `/admin emoji`.

## Vận hành
- **Sao lưu**: tự động mỗi `backup_interval_hours` giờ vào `backups/` (SQLite backup API, an toàn khi đang chạy, giữ `backup_keep` bản). Thủ công: `/admin sao_luu`. Khôi phục: dừng bot, chép một file `tbpt-*.db` đè lên `storage/than_bi_phuc_to.db`.
- **Migration**: thêm file `migrations/005_ten.sql` (không chứa BEGIN/COMMIT); lần khởi động kế tiếp tự áp, mỗi file một giao dịch. Hoặc `python tools/init_db.py`.
- **Vẽ lại emoji**: sửa lưới trong `tools/generate_emoji.py` rồi `python tools/generate_emoji.py` (cần Pillow), sau đó `/admin emoji`.
- **Tài liệu lệnh**: `python tools/gen_docs.py` sinh lại `COMMANDS.md` từ mã.
- **Kiểm thử**: `python -m unittest discover -s tests -t . -v`
- **Cân bằng**: `python tools/balance_sim.py 20000` (tỷ lệ sống sót từng lệ quỷ, kinh tế mỗi phiên); số liệu và các chỉnh đã làm ở `docs/BALANCE.md`
- **Log**: `logs/tbpt.log` (xoay vòng 2 MB × 3). Lỗi lệnh luôn được ghi kèm traceback, người chơi chỉ thấy thông báo thân thiện.

## Mở rộng
- Thêm lệ quỷ: một mục trong `data/ghosts.py` + một lớp trong `engine/mechanics.py` (`start/scene/act`) + thêm vào `MECHANICS`. Test dữ liệu sẽ nhắc nếu thiếu trường hay phá vòng khắc chế.
- Thêm địa điểm/vật phẩm/sự kiện/nhiệm vụ: chỉ sửa `data/*`. Thêm hệ thống mới: phát sự kiện lên `bus.emit(...)`, nhiệm vụ/thành tựu tự lắng nghe.
- Chuyển sang PostgreSQL: engine chỉ dùng `Database.one/all/run/tx`; thay lớp này và SQL tương thích.

## Giới hạn đã biết
Chưa chạy với discord.py/Discord thật trong môi trường tạo ra dự án (API đã đối chiếu một phần với tài liệu, xem REFERENCES.md); cân bằng game mới qua mô phỏng, chưa qua chơi thử người thật; mọi cơ chế lệ quỷ là thiết kế riêng, không phải lore chính thức. Chi tiết ở `TEST_REPORT.md` và `REFERENCES.md`.
