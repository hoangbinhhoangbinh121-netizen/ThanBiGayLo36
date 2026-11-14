"""Bộ dựng Embed DUY NHẤT: mọi màn hình dùng chung màu, tiêu đề, biểu tượng, thanh tiến trình, bố cục."""
from __future__ import annotations

import time

import discord

from data.basics import ACHIEVEMENTS, ITEM_CATS, ITEMS, MISSION_TYPES, ORIGINS, QUESTS, RANKS, REGIONS
from data.events import CONTRIB_ACTIONS, EVENT_DEFS
from data.ghosts import GHOSTS, RANK_NAME
from data.locations import LOCATIONS

COLOR = {"main": 0x6D1A1A, "info": 0x2B3A4A, "good": 0x2F6B4F, "bad": 0x8B1E1E, "mystic": 0x4B2A6B, "warn": 0x8A6A1E}
FOOTER = "Thần Bí Phục Tô  •  Bot By Tuyệt Thiên"
STATUS = {"binh_thuong": "Bình thường", "nhiem_linh_di": "Nhiễm linh dị", "mat_kiem_soat": "MẤT KIỂM SOÁT"}


def cut(s: str, n: int = 1024) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def ago(ts: int) -> str:
    d = max(0, int(time.time()) - ts)
    return f"{d // 3600}g trước" if d >= 3600 else f"{d // 60}p trước"


class UI:
    def __init__(self, emoji):
        self.emoji = emoji

    # ---- nền tảng ----------------------------------------------------------------
    def e(self, name: str) -> str:
        return self.emoji.fmt(name)

    def embed(self, title: str, desc: str = "", color: str = "main", icon: str | None = None, fields=()):
        e = discord.Embed(title=f"{self.e(icon)} {title}" if icon else title, description=cut(desc, 4000),
                          color=COLOR[color])
        for name, value, inline in fields:
            e.add_field(name=cut(name, 256), value=cut(value or "—"), inline=inline)
        e.set_footer(text=FOOTER)
        return e

    def bar(self, cur, mx, kind="hp", n=10) -> str:
        filled = 0 if mx <= 0 else max(0, min(n, round(n * cur / mx)))
        if f"bar_{kind}" in self.emoji.ids and "bar_empty" in self.emoji.ids:
            return self.e(f"bar_{kind}") * filled + self.e("bar_empty") * (n - filled)
        return "▰" * filled + "▱" * (n - filled)

    def error(self, msg: str):
        return self.embed("Không thể thực hiện", msg, "bad", "ui_that_bai")

    def success(self, title: str, msg: str):
        return self.embed(title, msg, "good", "ui_thanh_cong")

    def notices(self, lines):
        return self.embed("Thông báo", "\n".join(f"• {x}" for x in lines), "mystic", "ui_nguy_hiem")

    def item(self, item_id: str, qty: int | None = None) -> str:
        it = ITEMS[item_id]
        return f"{self.e(it['emoji'])} {it['name']}" + (f" ×{qty}" if qty is not None else "")

    # ---- hồ sơ ---------------------------------------------------------------------
    def profile(self, d: dict, mention: str = "") -> discord.Embed:
        p = d["p"]
        icon = ("char_mat_kiem_soat" if p["status"] == "mat_kiem_soat" else "char_nhiem_linh_di"
                if p["status"] == "nhiem_linh_di" else "char_ngu_quy_gia" if p["is_summoner"] else "char_nguoi_thuong")
        title = f"{p['name']} — {'Ngự Quỷ Giả' if p['is_summoner'] else 'Người thường'}"
        loc = LOCATIONS[p["location_id"]]
        org = d["org"]
        bal = d["balance"]
        fields = [
            (f"{self.e('ui_sinh_ton')} Thể chất", f"{self.bar(p['hp'], p['max_hp'], 'hp', 8)} {p['hp']}/{p['max_hp']}", False),
            (f"{self.e('char_nguoi_thuong')} Tinh thần", f"{self.bar(p['sanity'], p['max_sanity'], 'mind', 8)} "
                                                        f"{p['sanity']}/{p['max_sanity']}", False),
            (f"{self.e('ui_nguy_hiem')} Nhiễm linh dị", f"{self.bar(p['corruption'], 100, 'ghost', 8)} {p['corruption']}%", False),
            ("Hành trình", f"Cấp **{p['level']}**  •  EXP {p['exp']}/{d['exp_needed']}\n"
                           f"Danh tiếng **{p['reputation']}**  •  {self.e('item_tien_co')} **{p['coins']}** tiền cổ\n"
                           f"Xuất thân: {ORIGINS[p['origin']]['name']}", True),
            ("Trạng thái", f"{STATUS[p['status']]}\n{self.e(loc['emoji'])} {loc['name']}", True),
            (f"Lệ quỷ ({len(d['ghosts'])}/{d['slots']} khe, cân bằng {bal:+d})",
             "Chưa khống chế lệ quỷ nào." if not d["ghosts"] else "Phục tô càng cao càng dễ mất kiểm soát:", False),
        ]
        for g in d["ghosts"]:
            gd = GHOSTS[g["ghost_id"]]
            fields.append((f"{self.e(gd['emoji'])} {gd['name']}{' ✦' if g['awakened'] else ''}",
                           f"{self.bar(min(100, g['resurrection']), 100, 'ghost', 8)} {g['resurrection']:.0f}%", False))
        if d["sealed"]:
            fields.append(("Vật Chứa Vàng đang giữ", ", ".join(GHOSTS[g["ghost_id"]]["name"] for g in d["sealed"]), True))
        fields.append(("Tổ chức", f"{RANKS[org['rank']][1]} (khu {REGIONS.get(org['region'], '—')})" if org else "Chưa gia nhập",
                       True))
        fields.append(("Hồ sơ", f"{d['clues']} manh mối  •  {d['achievements']} thành tựu", True))
        e = self.embed(title, mention, "mystic" if p["is_summoner"] else "main", icon, fields)
        return e

    def history(self, rows):
        return self.embed("Lịch sử sự kiện", "\n".join(f"`{ago(r['ts'])}` {r['text']}" for r in rows) or "Chưa có gì.",
                          "info", "ui_nhiem_vu")

    def achievements(self, rows):
        lines = [f"{self.e('ui_thanh_cong') if got else self.e('ui_phong_an')} **{a['name']}** — {a['desc']} "
                 f"({prog}/{a['target']})" for _, a, got, prog in rows]
        return self.embed("Thành tựu", "\n".join(lines), "mystic", "ui_thanh_cong")

    # ---- thế giới --------------------------------------------------------------------
    def location(self, p, danger, lock, others) -> discord.Embed:
        loc = LOCATIONS[p["location_id"]]
        locked, reason, left = lock
        f = [("Nguy hiểm", f"{self.e('ui_nguy_hiem')} {danger}/10 {self.bar(danger, 10, 'hp', 10)}", True),
             ("Khu vực", REGIONS[loc["region"]], True)]
        if locked:
            f.append(("Phong tỏa", f"{reason} (còn ~{left // 60 + 1} phút)", False))
        if others:
            f.append(("Có thể đi tới", "\n".join(others), False))
        return self.embed(loc["name"], loc["desc"], "main", loc["emoji"], f)

    def world_map(self, ov, current, unrest, mods_text):
        lines = []
        for o in ov:
            loc = o["loc"]
            tag = " ◀ bạn ở đây" if o["id"] == current else ""
            lock = f" 🔒 {o['reason']} (~{o['left'] // 60 + 1}p)" if o["locked"] else ""
            lines.append(f"{self.e(loc['emoji'])} **{loc['name']}** — nguy hiểm {o['danger']}{lock}{tag}")
        fields = [("Bất ổn linh dị", f"{self.bar(unrest, 100, 'ghost')} {unrest}/100", False)]
        if mods_text:
            fields.append(("Hiệu ứng toàn thế giới", mods_text, False))
        return self.embed("Bản đồ Hắc Thủy Thành", "\n".join(lines), "info", "ui_kham_pha", fields)

    # ---- khám phá & đối mặt ----------------------------------------------------------------
    def explore_result(self, res, loc_name):
        color = {"clue": "mystic", "loot": "good", "encounter": "bad", "incident": "warn"}.get(res["kind"], "info")
        icon = {"clue": "ui_kham_pha", "loot": "item_tien_co", "encounter": "ui_nguy_hiem",
                "incident": "ui_nguy_hiem"}.get(res["kind"], "ui_kham_pha")
        return self.embed(f"{res['mode']} — {loc_name}", "\n".join(res["lines"]) + f"\n\n*Tiêu hao {res['cost']} tinh thần.*",
                          color, icon)

    def encounter(self, v, lines=()) -> discord.Embed:
        gd = v["ghost"]
        head = f"**{RANK_NAME[gd['rank']]}**  •  {gd['kill_rule'] if v['hints'] and v['phase'] == 'cleared' else ''}".strip(" •")
        if v["phase"] == "fight":
            desc = "\n".join(lines) + ("\n\n" if lines else "") + v["scene"].text
            fields = []
            if v["hints"]:
                fields.append(("Điều bạn đã biết về quy luật", "\n".join(f"• {h}" for h in v["hints"]), False))
            else:
                fields.append(("Quy luật", "Bạn chưa biết gì về nó. Mỗi lựa chọn đều là canh bạc.", False))
            if v["shield"]:
                fields.append(("Khiên bóng", f"{v['shield']} lớp", True))
            return self.embed(f"{gd['name']}", desc, "bad", gd["emoji"], fields)
        desc = "\n".join(lines) + "\n\nLệ quỷ đã lắng xuống. Bạn có thể khống chế, phong ấn, hoặc rời đi."
        fields = [("Khả năng khống chế", f"{v['bind_chance'] * 100:.0f}%", True),
                  ("Vật Chứa Vàng", "Có" if v["has_container"] else "Không có", True)]
        if v["already_held"]:
            fields.append(("Lưu ý", "Bạn đã giữ một lệ quỷ cùng loại, không thể khống chế thêm.", False))
        return self.embed(f"{gd['name']} — đã lắng xuống", desc, "good", gd["emoji"], fields)

    def encounter_end(self, title, lines, color="info", icon="ui_thanh_cong"):
        return self.embed(title, "\n".join(lines), color, icon)

    # ---- lệ quỷ ----------------------------------------------------------------------------------
    def ghost_list(self, owned, sealed, slots, balance):
        lines = []
        for g in owned:
            gd = GHOSTS[g["ghost_id"]]
            pw = ", ".join(p["name"] for p in gd["powers"])
            lines.append(f"{self.e(gd['emoji'])} **{gd['name']}** ({gd['rank']}){' ✦ thức tỉnh' if g['awakened'] else ''} "
                         f"— phục tô {g['resurrection']:.0f}%\n   Năng lực: {pw}  •  đã dùng {g['uses']} lần  •  mã `{g['id']}`")
        for g in sealed:
            gd = GHOSTS[g["ghost_id"]]
            lines.append(f"{self.e('item_vat_phong_an')} {gd['name']} (niêm phong) — mã `{g['id']}`")
        return self.embed("Lệ quỷ của bạn", "\n".join(lines) or "Bạn chưa giữ lệ quỷ nào.", "mystic", "ghost_quy_vuc",
                          [("Khe chứa", f"{len(owned)}/{slots}", True),
                           ("Cân bằng linh dị", f"{balance:+d} {'(mất cân bằng!)' if abs(balance) >= 3 else '(ổn định)'}", True)])

    def codex(self, data):
        f, gd = data["fields"], data["ghost"]
        if f["name"] == "???":
            return self.embed("???", "Bạn chưa biết gì về thứ này. Hãy khám phá để tìm manh mối.", "info", "ui_nguy_hiem")
        fields = [("Cấp độ nguy hiểm", RANK_NAME[f["rank"]], True),
                  ("Phạm vi ảnh hưởng", f["range"], False),
                  ("Quỷ vực", f"**{f['domain']['name']}** — {f['domain']['desc']}", False),
                  ("Quy luật giết người", f.get("kill_rule", "Chưa rõ. Cần manh mối."), False),
                  ("Cách đối phó", f.get("counter", "Chưa rõ. Cần manh mối."), False),
                  ("Điều kiện áp chế", f.get("suppress", "Chưa rõ. Cần manh mối."), False),
                  ("Phục tô", f"{gd['rate']}%/giờ khi bị giữ. Mỗi lần dùng năng lực làm phục tô tăng nhanh.", False)]
        if "awaken" in f:
            fields.append(("Thức tỉnh", f["awaken"], False))
        fields.append(("Manh mối đã có", f"{len(data['clues'])}/3", True))
        return self.embed(f["name"], f["origin"], "mystic", gd["emoji"], fields)

    # ---- vật phẩm ------------------------------------------------------------------------------
    def inventory(self, rows, coins):
        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(ITEMS[r["item_id"]]["cat"], []).append(r)
        fields = [(ITEM_CATS[c], "\n".join(f"{self.item(r['item_id'], r['qty'])}" for r in rs), False)
                  for c, rs in groups.items()]
        return self.embed("Túi đồ", f"{self.e('item_tien_co')} **{coins}** tiền cổ" + ("" if rows else "\n\nTúi trống."),
                          "main", "item_linh_di_vat", fields)

    def shop(self, stock, coins):
        lines = [f"{self.item(k)} — **{v['buy']}** (bán lại {v['sell']})\n   {v['desc']}" for k, v in stock.items()]
        return self.embed("Cửa hàng Tổng Bộ", f"Bạn có {self.e('item_tien_co')} **{coins}**\n\n" + "\n".join(lines), "main",
                          "item_tien_co")

    def trade(self, t, names):
        import json
        def side(s):
            parts = []
            if s["item"]:
                parts.append(self.item(s["item"], s["qty"]))
            if s["coins"]:
                parts.append(f"{self.e('item_tien_co')} {s['coins']}")
            return " + ".join(parts) or "không gì"
        give, want = json.loads(t["give_json"]), json.loads(t["want_json"])
        return self.embed(f"Giao dịch #{t['id']}", f"**{names[0]}** đưa: {side(give)}\n**{names[1]}** đưa: {side(want)}\n"
                                                  f"Hết hạn <t:{t['expires_at']}:R>", "warn", "item_tien_co")

    # ---- tổ chức ----------------------------------------------------------------------------------
    def org(self, info, member):
        o = info["org"]
        counts = "\n".join(f"{RANKS[r][1]}: {info['counts'].get(r, 0)}" for r in sorted(RANKS, key=lambda x: -RANKS[x][0]))
        f = [("Ngân quỹ", f"{self.e('item_tien_co')} {o['treasury']}", True), ("Nhiệm vụ đang mở", str(info["open_missions"]), True),
             ("Nhân sự", counts, False)]
        if info.get("vault"):
            f.append(("Kho giam giữ (Vật Chứa Vàng)", "\n".join(
                f"{self.e(GHOSTS[v['ghost_id']]['emoji'])} {GHOSTS[v['ghost_id']]['name']} ×{v['held']}" for v in info["vault"]), False))
        if member:
            f.append(("Bạn", f"{RANKS[member['rank']][1]}  •  khu {REGIONS.get(member['region'], '—')}  •  "
                             f"cống hiến {member['contribution']}", False))
        return self.embed(o["name"], "Cơ quan xử lý sự kiện linh dị. Tổng bộ điều hành, người phụ trách giữ từng khu vực.",
                          "info", "ui_phong_an", f)

    def archive(self, data):
        lines = []
        for r in data["rows"]:
            row, gd = r["row"], GHOSTS[r["row"]["ghost_id"]]
            lines.append(f"{self.e(gd['emoji'])} **{gd['name']}** ({gd['rank']}) — kho đang giữ {row['held']}, "
                         f"đã bàn giao {row['total_handed']} lần  •  bạn nắm {r['known']}/{len(gd['clues'])} manh mối")
        desc = "\n".join(lines) or ("Hồ sơ còn trống. Hồ sơ chỉ mở cho lệ quỷ mà một thành viên đã bàn giao Vật Chứa Vàng "
                                    "(`/quy ban_giao`).")
        return self.embed("Hồ sơ linh dị Tổng Bộ", desc + f"\n\nPhí đọc một manh mối: **{data['cost']}** tiền cổ (cấp càng cao càng rẻ; "
                          "Người Phụ Trách trở lên miễn phí). Dùng `/to_chuc ho_so_linh_di quy:<tên>`.", "info", "ui_nhiem_vu")

    def archive_read(self, r):
        gd = GHOSTS[r["ghost"]]
        return self.embed(f"Hồ sơ: {gd['name']}", f"{r['text']}\n\n*Phí: {r['cost']} tiền cổ. Manh mối đã ghi vào hồ sơ cá nhân của bạn.*",
                          "mystic", gd["emoji"])

    def org_members(self, rows):
        return self.embed("Thành viên Tổng Bộ", "\n".join(
            f"**{r['name']}** — {RANKS[r['rank']][1]} ({REGIONS.get(r['region'], '—')})  •  cống hiến {r['contribution']}"
            for r in rows) or "Chưa có ai.", "info", "ui_phong_an")

    def missions(self, rows):
        import json
        lines = []
        for r in rows:
            obj, rew = json.loads(r["objective_json"]), json.loads(r["reward_json"])
            who = f" → <@{r['assigned_to']}>" if r["assigned_to"] else ""
            lines.append(f"`#{r['id']}` **{r['title']}** [{r['status']}] {r['progress']}/{obj['n']} — thưởng "
                         f"{rew.get('coins', 0)} tiền cổ, hạn <t:{r['deadline']}:R>{who}")
        return self.embed("Nhiệm vụ tổ chức", "\n".join(lines) or "Không có nhiệm vụ nào phù hợp.", "info", "ui_nhiem_vu")

    def reports(self, rows):
        return self.embed("Báo cáo chờ duyệt", "\n".join(f"`#{r['id']}` **{r['name']}**: {cut(r['text'], 200)}" for r in rows)
                          or "Không có báo cáo nào chờ duyệt.", "info", "ui_nhiem_vu")

    def board(self, kind, rows):
        names = {"level": "Cấp độ", "reputation": "Danh tiếng", "seals": "Phong ấn", "clues": "Manh mối",
                 "contribution": "Cống hiến Tổng Bộ"}
        medal = ["🥇", "🥈", "🥉"]
        return self.embed(f"Bảng xếp hạng — {names[kind]}", "\n".join(
            f"{medal[i] if i < 3 else f'`{i + 1}.`'} **{n}** — {label}" for i, (n, label) in enumerate(rows)) or "Chưa có dữ liệu.",
                          "mystic", "ui_chien_dau")

    # ---- sự kiện & nhiệm vụ ---------------------------------------------------------------------------
    def events(self, rows, loc_of):
        lines = []
        for ev in rows:
            d = EVENT_DEFS[ev["def_id"]]
            extra = f" — {ev['progress']}/{ev['goal']} đóng góp" if ev["kind"] == "contrib" else ""
            lines.append(f"`#{ev['id']}` **{ev['title']}**{extra}\n   {d['desc']}\n   Kết thúc <t:{ev['ends_at']}:R>")
        acts = "\n".join(f"**{a['name']}** — {a['desc']}" for a in CONTRIB_ACTIONS.values())
        return self.embed("Sự kiện đang diễn ra", "\n\n".join(lines) or "Thế giới đang yên ắng... có lẽ vậy.", "warn", "ui_nguy_hiem",
                          [("Cách tham gia sự kiện địa điểm", "Có mặt tại hiện trường rồi dùng `/su_kien tham_gia`. Từ 3 người cùng tham gia, mỗi hành động được +1 yểm trợ.\n" + acts, False)])

    def quests(self, board):
        lines = []
        for b in board:
            q = b["q"]
            mark = {"done": self.e("ui_thanh_cong"), "active": self.e("ui_nhiem_vu"), "open": "▫"}[b["status"]]
            lock = f" (cần cấp {q['min_level']})" if b["locked"] else ""
            prog = f" {b['progress']}/{q['obj']['n']}" if b["status"] == "active" else ""
            lines.append(f"{mark} **{q['name']}**{lock}{prog} — {q['desc']}\n   Thưởng: {self.reward_text(q['reward'])}")
        return self.embed("Bảng nhiệm vụ", "\n".join(lines), "info", "ui_nhiem_vu")

    def reward_text(self, r):
        parts = []
        for k, label in (("coins", "tiền cổ"), ("exp", "EXP"), ("rep", "danh tiếng")):
            if r.get(k):
                parts.append(f"{r[k]} {label}")
        for i, n in r.get("items", {}).items():
            parts.append(f"{ITEMS[i]['name']} ×{n}")
        return ", ".join(parts) or "—"

    def story(self, v, extra=()):
        desc = "\n".join(extra) + ("\n\n" if extra else "") + v["text"]
        notes = "\n".join(f"• {c['label']}" + (f" 🔒 *{c['why']}*" if not c["ok"] else "") for c in v["choices"])
        return self.embed(v["title"], desc, "mystic", "item_thu_linh_di", [("Lựa chọn", notes, False)])

    def story_end(self, title, text, lines):
        return self.embed(f"{title} — kết cục", text + ("\n\n" + "\n".join(f"• {x}" for x in lines) if lines else ""),
                          "mystic", "item_thu_linh_di")

    # ---- trợ giúp --------------------------------------------------------------------------------------
    def help(self):
        groups = [
            ("Nhân vật", "/tao_nhan_vat  /ho_so  /nghi_ngoi  /lich_su  /thanh_tuu  /bxh  /xoa_nhan_vat"),
            ("Thế giới", "/ban_do  /dia_diem  /di_chuyen  /kham_pha  /doi_mat"),
            ("Ngự Quỷ Giả", "/quy danh_sach  /quy thong_tin  /quy nang_luc  /quy ap_che  /quy ban_giao  /ap_che_dong_doi"),
            ("Vật phẩm & kinh tế", "/kho_do  /dung_vat_pham  /cua_hang  /mua  /ban  /giao_dich moi|danh_sach|chap_nhan|tu_choi"),
            ("Sự kiện & nhiệm vụ", "/su_kien danh_sach|tham_gia|cau_chuyen  /nhiem_vu danh_sach|nhan"),
            ("Tổ chức", "/to_chuc gia_nhap|thong_tin|thanh_vien|nhiem_vu|nhan_nhiem_vu|giao_nhiem_vu|bao_cao|duyet_bao_cao|"
                        "ho_so_linh_di|thang_chuc|giang_chuc|loai|khu_vuc|nop_quy|mo_phong_toa|roi"),
            ("Quản trị", "/admin emoji|sao_luu|kenh|bo_nhiem|tang|mo_khoa|su_kien|xoa_nhan_vat|thong_ke"),
        ]
        return self.embed("Thần Bí Phục Tô — danh sách lệnh", "Bạn là Ngự Quỷ Giả trong một thế giới linh dị đang phục tô. "
                          "Lệ quỷ không thể bị đánh bại, chỉ có thể né quy luật, khống chế, hoặc phong ấn. "
                          "Khám phá để tìm manh mối; manh mối quyết định bạn sống hay chết.",
                          "main", "ghost_quy_thu", [(n, v, False) for n, v in groups])
