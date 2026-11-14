"""Người chơi: tạo nhân vật, chỉ số sinh tồn, cấp độ, chết, mất kiểm soát, hồi phục theo thời gian."""
from __future__ import annotations

from core.errors import GameError
from core.util import clamp
from data.basics import ORIGINS
from data.locations import HUB, LOCATIONS

MAX_LEVEL = 50
LOSS_SECONDS = 900           # thời gian mất kiểm soát
REGEN_HP, REGEN_SAN = 4, 6   # mỗi giờ
CORRUPT_ON, CORRUPT_OFF = 40, 30


def exp_needed(level: int) -> int:
    return 100 * level


class Service:
    def __init__(self, game):
        self.g = game

    @property
    def db(self):
        return self.g.db

    @property
    def clock(self):
        return self.g.clock

    @property
    def rng(self):
        return self.g.rng

    @property
    def bus(self):
        return self.g.bus


class PlayerService(Service):
    # ---- truy vấn ---------------------------------------------------------
    def exists(self, uid) -> bool:
        return self.db.one("SELECT 1 FROM players WHERE user_id=?", (uid,)) is not None

    def get(self, uid):
        r = self.db.one("SELECT * FROM players WHERE user_id=?", (uid,))
        if not r:
            raise GameError("Bạn chưa có nhân vật. Dùng /tao_nhan_vat để bắt đầu hành trình.")
        return r

    def log(self, uid, kind, text):
        self.db.run("INSERT INTO player_history(user_id,ts,kind,text) VALUES(?,?,?,?)",
                    (uid, self.clock.now(), kind, text))

    def history(self, uid, limit=10):
        return self.db.all("SELECT ts,kind,text FROM player_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                           (uid, limit))

    # ---- tạo nhân vật ---------------------------------------------------------
    def create(self, uid, name, origin_id):
        name = " ".join(str(name).split())
        if not 2 <= len(name) <= 24:
            raise GameError("Tên nhân vật phải từ 2 đến 24 ký tự.")
        o = ORIGINS.get(origin_id)
        if not o:
            raise GameError("Xuất thân không hợp lệ.")
        with self.db.tx():
            if self.exists(uid):
                raise GameError("Bạn đã có nhân vật rồi.")
            now = self.clock.now()
            self.db.run(
                "INSERT INTO players(user_id,name,origin,created_at,hp,max_hp,sanity,max_sanity,coins,location_id,last_regen_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (uid, name, origin_id, now, o["max_hp"], o["max_hp"], o["max_sanity"], o["max_sanity"],
                 o["coins"], HUB, now))
            for item, qty in o["items"].items():
                self.g.inv.add(uid, item, qty, quiet=True)
            self.log(uid, "created", f"Bước vào Hắc Thủy Thành với thân phận {o['name']}.")
        self.bus.emit("created", uid)
        return self.get(uid)

    def delete(self, uid) -> dict:
        """Xóa nhân vật và dọn mọi dữ liệu liên quan theo thứ tự an toàn (quỷ, nhiệm vụ tổ chức, báo cáo)."""
        with self.db.tx():
            p = self.get(uid)
            now = self.clock.now()
            bound = self.db.all("SELECT id FROM ghost_instances WHERE owner_id=? AND state='bound'", (uid,))
            if LOCATIONS[p["location_id"]].get("safe"):
                self.db.run("DELETE FROM ghost_instances WHERE owner_id=? AND state='bound'", (uid,))
            else:                                    # lệ quỷ tuột khỏi chủ nhân, ở lại nơi đó
                self.db.run("UPDATE ghost_instances SET state='free',owner_id=NULL,location_id=?,resurrection=0,"
                            "updated_at=? WHERE owner_id=? AND state='bound'", (p["location_id"], now, uid))
            sealed = self.db.run("DELETE FROM ghost_instances WHERE owner_id=? AND state='sealed'", (uid,)).rowcount
            for m in self.db.all("SELECT escrow,status FROM org_missions WHERE issued_by=?", (uid,)):
                if m["status"] in ("open", "taken"):
                    self.g.orgs.add_treasury(m["escrow"])        # hoàn quỹ nhiệm vụ chưa xong
            self.db.run("DELETE FROM org_missions WHERE issued_by=?", (uid,))
            self.db.run("UPDATE org_missions SET status='open',assigned_to=NULL WHERE assigned_to=? AND status='taken'", (uid,))
            self.db.run("UPDATE org_missions SET assigned_to=NULL WHERE assigned_to=?", (uid,))
            self.db.run("UPDATE org_reports SET reviewed_by=NULL WHERE reviewed_by=?", (uid,))
            self.db.run("DELETE FROM players WHERE user_id=?", (uid,))
            self.g.drain_notices(uid)
            return {"name": p["name"], "ghosts_released": len(bound), "sealed_lost": sealed}

    # ---- chỉ số -------------------------------------------------------------
    def adjust(self, uid, hp=0, sanity=0, corruption=0, coins=0, rep=0, exp=0, reason=""):
        """Thay đổi chỉ số nguyên tử. Tự xử lý lên cấp, chết, và sụp đổ tinh thần."""
        with self.db.tx():
            p = self.get(uid)
            nhp = clamp(p["hp"] + hp, 0, p["max_hp"])
            nsan = clamp(p["sanity"] + sanity, 0, p["max_sanity"])
            ncor = clamp(p["corruption"] + corruption, 0, 100)
            ncoins = max(0, p["coins"] + coins)
            nrep = max(0, p["reputation"] + rep)
            lvl, nexp, mhp, msan, ups = p["level"], p["exp"] + max(0, exp), p["max_hp"], p["max_sanity"], 0
            while lvl < MAX_LEVEL and nexp >= exp_needed(lvl):
                nexp -= exp_needed(lvl)
                lvl += 1
                ups += 1
                mhp += 5
                msan += 3
            if ups and nhp > 0:
                nhp = min(mhp, nhp + 10 * ups)
                nsan = min(msan, nsan + 5 * ups) if nsan > 0 else nsan
            if lvl >= MAX_LEVEL:
                nexp = 0
            self.db.run(
                "UPDATE players SET hp=?,sanity=?,corruption=?,coins=?,reputation=?,level=?,exp=?,max_hp=?,max_sanity=? "
                "WHERE user_id=?", (nhp, nsan, ncor, ncoins, nrep, lvl, nexp, mhp, msan, uid))
            self._sync_status(uid)
            res = {"level_up": ups, "level": lvl, "died": False, "saved": False, "breakdown": False}
            if ups:
                self.log(uid, "level", f"Đạt cấp {lvl}.")
                self.bus.emit("level_up", uid, level=lvl)
            if nhp <= 0:
                res.update(self.die(uid, reason or "Vết thương chí mạng"))
            elif nsan <= 0 and p["status"] != "mat_kiem_soat":
                self.breakdown(uid, "Tinh thần sụp đổ")
                res["breakdown"] = True
            return res

    def _sync_status(self, uid):
        p = self.db.one("SELECT status,corruption FROM players WHERE user_id=?", (uid,))
        if p["status"] == "binh_thuong" and p["corruption"] >= CORRUPT_ON:
            self.db.run("UPDATE players SET status='nhiem_linh_di' WHERE user_id=?", (uid,))
        elif p["status"] == "nhiem_linh_di" and p["corruption"] < CORRUPT_OFF:
            self.db.run("UPDATE players SET status='binh_thuong' WHERE user_id=?", (uid,))

    def die(self, uid, cause="Không rõ nguyên nhân"):
        """Hình Nhân Thế Mạng cứu một lần; nếu không: hồi sinh ở Khu Trung Tâm với tổn thất."""
        with self.db.tx():
            p = self.get(uid)
            self.db.run("DELETE FROM encounters WHERE user_id=?", (uid,))
            if self.g.inv.count(uid, "hinh_nhan") > 0:
                self.g.inv.remove(uid, "hinh_nhan", 1)
                self.db.run("UPDATE players SET hp=1 WHERE user_id=?", (uid,))
                self.log(uid, "saved", f"Hình Nhân Thế Mạng vỡ vụn thay bạn ({cause}).")
                return {"died": False, "saved": True}
            lost_coins, lost_exp = int(p["coins"] * 0.3), int(p["exp"] * 0.2)
            self.db.run(
                "UPDATE players SET hp=?,sanity=?,coins=coins-?,exp=exp-?,corruption=MIN(100,corruption+10),"
                "location_id=?,status='binh_thuong',status_until=0,last_regen_at=? WHERE user_id=?",
                (max(1, p["max_hp"] // 2), max(1, p["max_sanity"] // 2), lost_coins, lost_exp, HUB,
                 self.clock.now(), uid))
            for g in self.db.all("SELECT id,resurrection FROM ghost_instances WHERE owner_id=? AND state='bound'", (uid,)):
                self.db.run("UPDATE ghost_instances SET resurrection=MIN(99,resurrection+20) WHERE id=?", (g["id"],))
            self._sync_status(uid)
            self.log(uid, "died", f"Tử vong: {cause}. Mất {lost_coins} tiền cổ, {lost_exp} kinh nghiệm.")
            self.bus.emit("died", uid, cause=cause)
            return {"died": True, "saved": False, "lost_coins": lost_coins, "lost_exp": lost_exp}

    def breakdown(self, uid, why):
        """Mất kiểm soát: bị khóa hành động, lệ quỷ đang giữ phục tô thêm."""
        with self.db.tx():
            p = self.get(uid)
            now = self.clock.now()
            self.db.run(
                "UPDATE players SET status='mat_kiem_soat',status_until=?,sanity=MAX(1,max_sanity/10),"
                "hp=MAX(1,hp-max_hp*15/100),corruption=MIN(100,corruption+8) WHERE user_id=?",
                (now + LOSS_SECONDS, uid))
            self.db.run("DELETE FROM encounters WHERE user_id=?", (uid,))
            for g in self.db.all("SELECT id FROM ghost_instances WHERE owner_id=? AND state='bound'", (uid,)):
                self.db.run("UPDATE ghost_instances SET resurrection=resurrection+25 WHERE id=?", (g["id"],))
            self.log(uid, "lost_control", f"Mất kiểm soát: {why}.")
            self.bus.emit("lost_control", uid, why=why)
            self.g.ghosts.check_resurrections(uid)

    def end_lost_control(self, uid):
        self.db.run("UPDATE players SET status='binh_thuong',status_until=0 WHERE user_id=?", (uid,))
        self._sync_status(uid)

    # ---- làm mới theo thời gian ---------------------------------------------------
    def refresh(self, uid):
        """Gọi đầu mọi hành động: hết hạn trạng thái, hồi phục, phục tô của lệ quỷ."""
        with self.db.tx():
            self.g.ghosts.tick_owner(uid)
            p = self.get(uid)
            now = self.clock.now()
            if p["status"] == "mat_kiem_soat" and now >= p["status_until"]:
                self.end_lost_control(uid)
                p = self.get(uid)
            if p["status"] != "mat_kiem_soat":
                hours = (now - p["last_regen_at"]) / 3600
                mult = 2.0 if LOCATIONS[p["location_id"]].get("safe") else 1.0
                san_mult = 0.5 if p["corruption"] >= CORRUPT_ON else 1.0
                dh, ds = int(hours * REGEN_HP * mult), int(hours * REGEN_SAN * mult * san_mult)
                if dh or ds:
                    self.db.run("UPDATE players SET hp=MIN(max_hp,hp+?),sanity=MIN(max_sanity,sanity+?),last_regen_at=? "
                                "WHERE user_id=?", (dh, ds, now, uid))
            else:
                self.db.run("UPDATE players SET last_regen_at=? WHERE user_id=?", (now, uid))
            return self.get(uid)

    def require_free(self, uid):
        """Người chơi phải đang hành động được: không mất kiểm soát, không trong đối mặt."""
        p = self.refresh(uid)
        if p["status"] == "mat_kiem_soat":
            left = max(0, p["status_until"] - self.clock.now())
            raise GameError(f"Bạn đang mất kiểm soát, còn khoảng {left // 60 + 1} phút. "
                            "Đồng đội có thể dùng Bùa Áp Chế để kéo bạn ra.")
        if self.db.one("SELECT 1 FROM encounters WHERE user_id=?", (uid,)):
            raise GameError("Bạn đang đối mặt với một lệ quỷ. Hãy giải quyết cuộc đối mặt trước.")
        return p

    # ---- cooldown & buff ----------------------------------------------------------
    def check_cooldown(self, uid, key, seconds):
        now = self.clock.now()
        r = self.db.one("SELECT until_ts FROM cooldowns WHERE user_id=? AND key=?", (uid, key))
        if r and r["until_ts"] > now:
            raise GameError(f"Chờ thêm {r['until_ts'] - now} giây nữa.")
        self.db.run("INSERT INTO cooldowns(user_id,key,until_ts) VALUES(?,?,?) "
                    "ON CONFLICT(user_id,key) DO UPDATE SET until_ts=excluded.until_ts", (uid, key, now + seconds))

    def set_buff(self, uid, key, value, seconds=86400):
        self.db.run("INSERT INTO buffs(user_id,key,value,until_ts) VALUES(?,?,?,?) "
                    "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,until_ts=excluded.until_ts",
                    (uid, key, value, self.clock.now() + seconds))

    def buff(self, uid, key) -> int:
        r = self.db.one("SELECT value FROM buffs WHERE user_id=? AND key=? AND until_ts>?", (uid, key, self.clock.now()))
        return r["value"] if r else 0

    def use_buff(self, uid, key) -> int:
        """Tiêu một tầng buff, trả giá trị trước khi tiêu (0 nếu không có)."""
        v = self.buff(uid, key)
        if v > 1:
            self.db.run("UPDATE buffs SET value=value-1 WHERE user_id=? AND key=?", (uid, key))
        elif v == 1:
            self.db.run("DELETE FROM buffs WHERE user_id=? AND key=?", (uid, key))
        return v

    # ---- hồ sơ ---------------------------------------------------------------------
    def profile(self, uid) -> dict:
        p = self.refresh(uid)
        return {
            "p": p,
            "ghosts": self.g.ghosts.owned(uid),
            "sealed": self.g.ghosts.sealed_by(uid),
            "org": self.g.orgs.member(uid),
            "achievements": self.db.scalar("SELECT COUNT(*) FROM player_achievements WHERE user_id=?", (uid,), 0),
            "clues": self.db.scalar("SELECT COUNT(*) FROM player_clues WHERE user_id=?", (uid,), 0),
            "slots": self.g.ghosts.max_slots(p),
            "balance": self.g.ghosts.balance(uid),
            "exp_needed": exp_needed(p["level"]),
        }
