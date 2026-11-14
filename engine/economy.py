"""Túi đồ, cửa hàng NPC, giao dịch giữa người chơi, nghỉ ngơi, và hệ thống hiệu ứng dùng chung."""
from __future__ import annotations

import json

from core.errors import GameError
from data.basics import ITEMS
from data.ghosts import GHOSTS
from data.locations import HUB, LOCATIONS
from engine.players import Service

REST_COST = 15
TRADE_TTL = 600
MAX_PENDING_TRADES = 3


def item_name(item_id):
    return ITEMS[item_id]["name"]


class InventoryService(Service):
    def count(self, uid, item_id) -> int:
        return self.db.scalar("SELECT qty FROM inventory WHERE user_id=? AND item_id=?", (uid, item_id), 0)

    def list(self, uid):
        return self.db.all("SELECT item_id,qty FROM inventory WHERE user_id=? ORDER BY item_id", (uid,))

    def add(self, uid, item_id, qty=1, quiet=False):
        if item_id not in ITEMS:
            raise GameError(f"Vật phẩm không tồn tại: {item_id}")
        if qty <= 0:
            raise GameError("Số lượng phải dương.")
        self.db.run("INSERT INTO inventory(user_id,item_id,qty) VALUES(?,?,?) "
                    "ON CONFLICT(user_id,item_id) DO UPDATE SET qty=qty+excluded.qty", (uid, item_id, qty))
        if not quiet:
            self.bus.emit("item_gained", uid, item=item_id, qty=qty)

    def remove(self, uid, item_id, qty=1):
        have = self.count(uid, item_id)
        if qty <= 0 or have < qty:
            raise GameError(f"Bạn không đủ {item_name(item_id)} (có {have}, cần {qty}).")
        if have == qty:
            self.db.run("DELETE FROM inventory WHERE user_id=? AND item_id=?", (uid, item_id))
        else:
            self.db.run("UPDATE inventory SET qty=qty-? WHERE user_id=? AND item_id=?", (qty, uid, item_id))

    def use(self, uid, item_id, target_inst_id=None) -> list[str]:
        """Dùng vật phẩm ngoài đối mặt."""
        with self.db.tx():
            self.g.players.require_free(uid)
            it = ITEMS.get(item_id)
            if not it:
                raise GameError("Vật phẩm không tồn tại.")
            if self.count(uid, item_id) < 1:
                raise GameError(f"Bạn không có {it['name']}.")
            if "use" in it:
                self.remove(uid, item_id)
                lines = apply_effects(self.g, uid, it["use"], f"Dùng {it['name']}")
                return [f"Đã dùng {it['name']}."] + lines
            if item_id == "bua_ap_che":
                inst = self.g.ghosts.get_owned(uid, target_inst_id)
                self.remove(uid, item_id)
                new = self.g.ghosts.reduce_resurrection(inst["id"], 30)
                return [f"Bùa Áp Chế dán lên {GHOSTS[inst['ghost_id']]['name']}: phục tô còn {new:.0f}%."]
            if item_id == "thu_linh_di":
                return self.g.events.start_story(uid, "thu_linh_di")
            raise GameError(f"{it['name']} chỉ dùng được trong đối mặt hoặc theo điều kiện riêng.")


def apply_effects(g, uid, fx: dict, reason="") -> list[str]:
    """Điểm áp hiệu ứng DUY NHẤT cho sự cố, kết cục sự kiện, thưởng nhiệm vụ, thưởng tổ chức..."""
    lines: list[str] = []
    res = g.players.adjust(
        uid, hp=fx.get("hp", 0), sanity=fx.get("sanity", 0), corruption=fx.get("corruption", 0),
        coins=fx.get("coins", 0), rep=fx.get("rep", 0), exp=fx.get("exp", 0), reason=reason)
    names = (("hp", "Thể chất"), ("sanity", "Tinh thần"), ("corruption", "Nhiễm linh dị"),
             ("coins", "Tiền cổ"), ("rep", "Danh tiếng"), ("exp", "Kinh nghiệm"))
    for k, label in names:
        if fx.get(k):
            lines.append(f"{'+' if fx[k] > 0 else ''}{fx[k]} {label}")
    for item, qty in fx.get("items", {}).items():
        g.inv.add(uid, item, qty)
        lines.append(f"+{qty} {item_name(item)}")
    for ghost_id, idx in fx.get("clues", []):
        if g.ghosts.add_clue(uid, ghost_id, idx):
            lines.append(f"Manh mối mới về {GHOSTS[ghost_id]['name']}")
    w = fx.get("world")
    if w:
        g.world.apply_world_effects(w)
    if res["level_up"]:
        lines.append(f"Lên cấp {res['level']}!")
    if res["saved"]:
        lines.append("Hình Nhân Thế Mạng đã vỡ thay bạn.")
    elif res["died"]:
        lines.append("Bạn đã chết.")
    if res["breakdown"]:
        lines.append("Tinh thần sụp đổ: bạn mất kiểm soát!")
    return lines


class EconomyService(Service):
    # ---- cửa hàng -----------------------------------------------------------
    def _need_shop(self, uid):
        p = self.g.players.require_free(uid)
        if not LOCATIONS[p["location_id"]].get("shop"):
            raise GameError("Cửa hàng chỉ có ở Khu Trung Tâm.")
        return p

    def stock(self):
        return {k: v for k, v in ITEMS.items() if v.get("buy")}

    def buy(self, uid, item_id, qty=1):
        if not 1 <= qty <= 20:
            raise GameError("Mỗi lần mua từ 1 đến 20 món.")
        it = ITEMS.get(item_id)
        if not it or not it.get("buy"):
            raise GameError("Cửa hàng không bán món này.")
        with self.db.tx():
            p = self._need_shop(uid)
            cost = it["buy"] * qty
            if p["coins"] < cost:
                raise GameError(f"Cần {cost} tiền cổ, bạn chỉ có {p['coins']}.")
            self.g.players.adjust(uid, coins=-cost)
            self.g.inv.add(uid, item_id, qty)
            self.g.players.log(uid, "buy", f"Mua {qty} {it['name']} giá {cost}.")
        return cost

    def sell(self, uid, item_id, qty=1):
        it = ITEMS.get(item_id)
        if not it or qty < 1:
            raise GameError("Vật phẩm hoặc số lượng không hợp lệ.")
        with self.db.tx():
            self._need_shop(uid)
            self.g.inv.remove(uid, item_id, qty)
            gain = it["sell"] * qty
            self.g.players.adjust(uid, coins=gain)
            self.g.players.log(uid, "sell", f"Bán {qty} {it['name']} được {gain}.")
        return gain

    # ---- nghỉ ngơi ------------------------------------------------------------------
    def rest(self, uid):
        with self.db.tx():
            p = self.g.players.require_free(uid)
            if not LOCATIONS[p["location_id"]].get("safe"):
                raise GameError("Chỉ nghỉ ngơi được ở nơi an toàn (Khu Trung Tâm).")
            if p["coins"] < REST_COST:
                raise GameError(f"Nhà nghỉ an toàn thu {REST_COST} tiền cổ.")
            self.g.players.check_cooldown(uid, "rest", 600)
            self.g.players.adjust(uid, coins=-REST_COST, hp=p["max_hp"] // 2, sanity=int(p["max_sanity"] * 0.6),
                                  corruption=-5)
            for gh in self.g.ghosts.owned(uid):
                self.g.ghosts.reduce_resurrection(gh["id"], 10)
            self.g.players.log(uid, "rest", "Nghỉ trong căn nhà dán vàng lá.")
        return self.g.players.get(uid)

    # ---- giao dịch ------------------------------------------------------------------------
    def _parse(self, side: dict):
        out = {"coins": int(side.get("coins", 0)), "item": side.get("item"), "qty": int(side.get("qty", 0))}
        if out["coins"] < 0 or out["qty"] < 0:
            raise GameError("Số lượng không được âm.")
        if out["item"]:
            it = ITEMS.get(out["item"])
            if not it:
                raise GameError("Vật phẩm giao dịch không tồn tại.")
            if not it.get("tradable"):
                raise GameError(f"{it['name']} không thể giao dịch.")
            if out["qty"] < 1:
                raise GameError("Hãy ghi số lượng vật phẩm.")
        else:
            out["qty"] = 0
        return out

    def _has(self, uid, side):
        p = self.g.players.get(uid)
        if p["coins"] < side["coins"]:
            raise GameError("Một bên không đủ tiền cổ cho giao dịch.")
        if side["item"] and self.g.inv.count(uid, side["item"]) < side["qty"]:
            raise GameError("Một bên không đủ vật phẩm cho giao dịch.")

    def offer(self, from_uid, to_uid, give: dict, want: dict) -> int:
        if from_uid == to_uid:
            raise GameError("Không thể giao dịch với chính mình.")
        give, want = self._parse(give), self._parse(want)
        if not (give["coins"] or give["item"] or want["coins"] or want["item"]):
            raise GameError("Giao dịch trống.")
        with self.db.tx():
            self.g.players.require_free(from_uid)
            self.g.players.get(to_uid)
            self._expire_trades()
            if self.db.scalar("SELECT COUNT(*) FROM trades WHERE from_user=? AND status='pending'", (from_uid,), 0) \
                    >= MAX_PENDING_TRADES:
                raise GameError(f"Bạn đang có {MAX_PENDING_TRADES} lời mời giao dịch chưa xử lý.")
            self._has(from_uid, give)
            now = self.clock.now()
            cur = self.db.run("INSERT INTO trades(from_user,to_user,give_json,want_json,created_at,expires_at) "
                              "VALUES(?,?,?,?,?,?)",
                              (from_uid, to_uid, json.dumps(give), json.dumps(want), now, now + TRADE_TTL))
            return cur.lastrowid

    def _expire_trades(self):
        self.db.run("UPDATE trades SET status='expired' WHERE status='pending' AND expires_at<=?", (self.clock.now(),))

    def pending_for(self, uid):
        self._expire_trades()
        return self.db.all("SELECT * FROM trades WHERE to_user=? AND status='pending' ORDER BY id", (uid,))

    def accept(self, uid, trade_id):
        with self.db.tx():
            self._expire_trades()
            t = self.db.one("SELECT * FROM trades WHERE id=?", (trade_id,))
            if not t or t["status"] != "pending":
                raise GameError("Giao dịch không còn hiệu lực.")
            if t["to_user"] != uid:
                raise GameError("Đây không phải giao dịch gửi cho bạn.")
            self.g.players.require_free(uid)
            give, want = json.loads(t["give_json"]), json.loads(t["want_json"])
            a, b = t["from_user"], t["to_user"]
            self._has(a, give)
            self._has(b, want)
            for src, dst, side in ((a, b, give), (b, a, want)):
                if side["coins"]:
                    self.g.players.adjust(src, coins=-side["coins"])
                    self.g.players.adjust(dst, coins=side["coins"])
                if side["item"]:
                    self.g.inv.remove(src, side["item"], side["qty"])
                    self.g.inv.add(dst, side["item"], side["qty"])
            self.db.run("UPDATE trades SET status='accepted' WHERE id=?", (trade_id,))
            self.g.players.log(a, "trade", f"Giao dịch #{trade_id} hoàn tất.")
            self.g.players.log(b, "trade", f"Giao dịch #{trade_id} hoàn tất.")
            self.bus.emit("trade_done", a)
            self.bus.emit("trade_done", b)
        return t

    def decline(self, uid, trade_id):
        with self.db.tx():
            t = self.db.one("SELECT * FROM trades WHERE id=? AND status='pending'", (trade_id,))
            if not t or uid not in (t["to_user"], t["from_user"]):
                raise GameError("Không tìm thấy giao dịch đang chờ của bạn.")
            self.db.run("UPDATE trades SET status=? WHERE id=?",
                        ("declined" if uid == t["to_user"] else "cancelled", trade_id))
