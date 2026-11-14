"""Cơ chế đối mặt RIÊNG cho từng lệ quỷ (thiết lập riêng của game).

Mỗi cơ chế là một máy trạng thái độc lập: không dùng chung bộ chỉ số, mà dùng chung giao diện
start / scene / act. Biết manh mối (known) sẽ hé lộ thông tin giúp người chơi chọn đúng.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Opt:
    id: str
    label: str
    desc: str = ""
    item: str | None = None   # vật phẩm cần có; bị tiêu khi chọn


@dataclass
class Scene:
    text: str
    options: list


@dataclass
class Step:
    text: str
    outcome: str = "continue"          # continue | survive | death
    dmg: dict = field(default_factory=dict)   # delta hp / sanity / corruption
    fx: dict = field(default_factory=dict)    # hiệu ứng thưởng (apply_effects)
    bind_bonus: float = 0.0


class Mechanic:
    id = ""
    can_flee = True

    def start(self, rng) -> dict:
        raise NotImplementedError

    def scene(self, st, known, has) -> Scene:
        raise NotImplementedError

    def act(self, st, opt, rng, p) -> Step:
        raise NotImplementedError

    def boost(self, st):
        """Năng lực 'progress' của lệ quỷ đang giữ."""


# ---------------------------------------------------------------- Quỷ Thủ: giữ yên, đừng chống cự
class QuyThu(Mechanic):
    id = "quy_thu"

    def start(self, rng):
        return {"grip": 0, "hold": 0, "goal": 3, "shield": 0}

    def scene(self, st, known, has):
        lines = ["Một bàn tay lạnh buốt vừa nắm lấy cổ chân bạn.",
                 "Bàn tay siết chặt hơn, móng cắm vào da thịt.",
                 "Xương cổ chân kêu răng rắc dưới lực siết."]
        text = lines[min(2, (st["grip"] + 1) // 2)]
        if 0 in known:
            text += f"\n[Độ siết {st['grip']}/5 | Bình tĩnh {st['hold']}/{st['goal']}]"
        opts = [Opt("dung_yen", "Đứng yên, nín thở"), Opt("giay_dua", "Giãy giụa kéo chân ra"),
                Opt("nhin_xuong", "Cúi xuống nhìn bàn tay")]
        if has("hinh_nhan"):
            opts.append(Opt("dua_vat", "Dúi Hình Nhân Thế Mạng cho nó", item="hinh_nhan"))
        return Scene(text, opts)

    def act(self, st, opt, rng, p):
        if opt == "dung_yen":
            st["hold"] += 1
            st["grip"] = max(0, st["grip"] - 1)
            if st["hold"] >= st["goal"]:
                return Step("Bàn tay run lên, nới ra rồi tan vào bóng tối.", "survive")
            return Step("Bạn đứng yên. Bàn tay do dự, lực siết nhẹ đi một chút.")
        if opt == "giay_dua":
            st["hold"] = max(0, st["hold"] - 1)
            if st["shield"] > 0:
                st["shield"] -= 1
                return Step("Bóng ma của bạn gạt bàn tay ra, nhưng nó vẫn bám lấy.")
            st["grip"] += 2
            if st["grip"] >= 5:
                return Step("Bàn tay siết gãy cổ chân bạn và lôi xuống gầm tối.", "death", {"hp": -30})
            return Step("Càng giãy, bàn tay càng siết sâu.", dmg={"hp": -8})
        if opt == "nhin_xuong":
            st["grip"] += 1
            if st["grip"] >= 5:
                return Step("Bạn nhìn thấy nó đang nhìn lại. Bàn tay kéo bạn xuống.", "death")
            return Step("Bàn tay xanh đen có quá nhiều ngón. Nó biết bạn đã nhìn.", dmg={"sanity": -6})
        if opt == "dua_vat":
            return Step("Bàn tay buông bạn ra, nắm lấy hình nhân giấy rồi lùi vào bóng tối.", "survive", bind_bonus=0.15)
        return Step("Bạn do dự.")

    def boost(self, st):
        st["hold"] += 1


# ---------------------------------------------------------------- Quỷ Ảnh: tránh đúng MỘT nguồn sáng
LIGHT_DESC = {0: "Góc tối, không một ngọn đèn", 1: "Dưới một ngọn đèn leo lét", 2: "Giữa hai ngọn đèn chồng bóng"}


class QuyAnh(Mechanic):
    id = "quy_anh"

    def _roll(self, rng):
        spots = [0, 1, 2]
        rng.shuffle(spots)
        return spots

    def start(self, rng):
        return {"round": 1, "rounds": 4, "strikes": 0, "shield": 0, "spots": self._roll(rng)}

    def scene(self, st, known, has):
        text = f"Vòng {st['round']}/{st['rounds']}. Bóng đen trườn trên tường, tìm chỗ để dẫm lên bóng bạn."
        if 0 in known:
            text += f"\n[Bị dẫm {st['strikes']}/2]"
        opts = []
        for i, light in enumerate(st["spots"]):
            desc = LIGHT_DESC[light] + (" - ⚠ nơi nó chờ" if 0 in known and light == 1 else "")
            opts.append(Opt(f"spot{i}", f"Đứng ở vị trí {'ABC'[i]}", desc))
        if has("den_dau"):
            opts.append(Opt("dung_den", "Thắp đèn dầu xua bóng", "Bỏ qua vòng này", item="den_dau"))
        return Scene(text, opts)

    def _advance(self, st, rng, text):
        st["round"] += 1
        if st["round"] > st["rounds"]:
            return Step(text + " Bóng đen rút đi, hành lang sáng lên.", "survive", dmg={"sanity": -2})
        st["spots"] = self._roll(rng)
        return Step(text, dmg={"sanity": -2})

    def act(self, st, opt, rng, p):
        if opt == "dung_den":
            return self._advance(st, rng, "Ngọn đèn dầu xua bóng lùi lại.")
        light = st["spots"][int(opt[4:])]
        if light != 1:
            return self._advance(st, rng, "Bóng đen trượt qua mà không chạm được bạn.")
        if st["shield"] > 0:
            st["shield"] -= 1
            return self._advance(st, rng, "Bóng đen dẫm xuống, nhưng khiên bóng của bạn nuốt trọn cú dẫm.")
        st["strikes"] += 1
        if st["strikes"] >= 2:
            return Step("Bóng đen dẫm lên bóng bạn lần thứ hai. Dưới đèn chỉ còn một cái bóng.", "death")
        s = self._advance(st, rng, "Bóng đen dẫm lên bóng bạn. Cơ thể lạnh buốt.")
        s.dmg = {"hp": -15, "sanity": -10}
        return s

    def boost(self, st):
        st["strikes"] = max(0, st["strikes"] - 1)


# ---------------------------------------------------------------- Quỷ Nhãn: nhìn - nhắm luân phiên
class QuyNhan(Mechanic):
    id = "quy_nhan"

    def start(self, rng):
        return {"gaze": 0, "dist": 4, "shield": 0}

    def scene(self, st, known, has):
        text = "Một con mắt khổng lồ mở trừng giữa bóng tối, nhìn thẳng vào bạn."
        if 0 in known:
            text += f"\n[Ánh nhìn {st['gaze']}/3 | Khoảng cách {st['dist']}/6 (6 = thoát) | 0 = bị nuốt]"
        opts = [Opt("nhin", "Nhìn thẳng vào nó", "Biết thêm, nhưng ánh nhìn bám lấy bạn"),
                Opt("nham_mat", "Nhắm mắt lại", "Xóa ánh nhìn, nhưng nó tiến gần"),
                Opt("lui", "Lùi lại từng bước", "Đi xa hơn, nhưng vẫn phải nhìn")]
        if has("guong_nut"):
            opts.append(Opt("dung_guong", "Soi Gương Nứt vào mắt nó", "Đẩy nó lùi xa", item="guong_nut"))
        return Scene(text, opts)

    def _gaze(self, st):
        if st["shield"] > 0:
            st["shield"] -= 1
            return False
        st["gaze"] += 1
        return True

    def act(self, st, opt, rng, p):
        if opt == "nhin":
            self._gaze(st)
            if st["gaze"] >= 3:
                return Step("Bạn không rời mắt được nữa. Con mắt nuốt chửng bạn.", "death")
            return Step("Con mắt đỏ ngầu, mạch máu đập theo nhịp tim bạn.", dmg={"sanity": -4})
        if opt == "nham_mat":
            st["gaze"] = 0
            st["dist"] -= 1
            if st["dist"] <= 0:
                return Step("Bạn mở mắt ra. Chỉ còn một màu đỏ.", "death")
            return Step("Bạn nhắm mắt. Dấu ấn trên người tan đi, nhưng hơi lạnh tiến sát hơn.")
        if opt == "lui":
            st["dist"] += 1
            self._gaze(st)
            if st["dist"] >= 6:
                return Step("Bạn lùi khỏi tầm nhìn. Con mắt khép lại từ từ.", "survive")
            if st["gaze"] >= 3:
                return Step("Bạn quên cách quay đi. Con mắt nuốt chửng bạn.", "death")
            return Step("Bạn lùi một bước, mắt vẫn dán chặt vào nó.", dmg={"sanity": -2})
        if opt == "dung_guong":
            st["dist"] += 2
            st["gaze"] = 0
            if st["dist"] >= 6:
                return Step("Gương nứt phản chiếu ánh nhìn: con mắt rụt lại, khép chặt.", "survive", dmg={"sanity": -5})
            return Step("Gương nứt đẩy ánh nhìn của nó lùi xa.", dmg={"sanity": -5})
        return Step("Bạn do dự.")

    def boost(self, st):
        st["dist"] += 1


# ---------------------------------------------------------------- Quỷ Quan Tài: đừng nằm vào
class QuyQuanTai(Mechanic):
    id = "quy_quan_tai"

    def start(self, rng):
        return {"lid": 0, "shield": 0}

    def scene(self, st, known, has):
        text = "Cỗ quan tài mở nắp giữa phòng. Một giọng thì thầm: 'Mệt rồi mà... nằm xuống đi...'"
        if 0 in known:
            text += f"\n[Nắp đã khép {st['lid']}/3]"
        opts = [Opt("nam_vao", "Nằm vào quan tài", "Nghỉ một chút"),
                Opt("dong_nap", "Gắng sức đóng nắp lại", "Cần ý chí còn vững")]
        if has("hinh_nhan"):
            opts.append(Opt("dat_hinh_nhan", "Đặt Hình Nhân vào quan tài", item="hinh_nhan"))
        if has("quan_tai_nho"):
            opts.append(Opt("dat_quan_tai", "Đặt Quan Tài Nhỏ lên nắp", item="quan_tai_nho"))
        if has("dinh_quan_tai"):
            opts.append(Opt("dong_dinh", "Đóng Đinh Quan Tài Vàng", item="dinh_quan_tai"))
        return Scene(text, opts)

    def act(self, st, opt, rng, p):
        if opt == "nam_vao":
            return Step("Bạn nằm xuống. Nắp khép lại nhẹ nhàng, rất nhẹ nhàng.", "death")
        if opt == "dong_nap":
            if p["sanity"] < 12:
                return Step("Giọng mời gọi bóp nát ý chí cuối cùng. Chân bạn tự bước tới.", "death")
            if st["shield"] > 0:
                st["shield"] -= 1
                st["lid"] += 1
                step = Step("Bóng ma của bạn gánh phần sức nặng; nắp khép thêm một đoạn.")
            else:
                st["lid"] += 1
                step = Step("Bạn nghiến răng đẩy nắp. Giọng thì thầm gào lên trong đầu.", dmg={"hp": -8, "sanity": -8})
            if st["lid"] >= 3:
                step.text = "Nắp quan tài khép lại. Giọng thì thầm tắt dần."
                step.outcome = "survive"
            return step
        if opt in ("dat_hinh_nhan", "dat_quan_tai"):
            return Step("Có thứ nằm vào. Nắp tự khép lại, êm ru.", "survive", bind_bonus=0.1)
        if opt == "dong_dinh":
            return Step("Đinh vàng xuyên qua nắp. Giọng nói tắt hẳn; quan tài im lìm.", "survive", bind_bonus=0.3)
        return Step("Bạn do dự.")

    def boost(self, st):
        st["lid"] += 1


# ---------------------------------------------------------------- Quỷ Môn: gõ lẻ là của nó
class QuyMon(Mechanic):
    id = "quy_mon"

    def start(self, rng):
        return {"round": 1, "rounds": 4, "strikes": 0, "shield": 0, "knocks": rng.randint(1, 5)}

    def scene(self, st, known, has):
        text = f"Vòng {st['round']}/{st['rounds']}. Sau cánh cửa vang lên {st['knocks']} tiếng gõ."
        if 0 in known:
            text += "\n[Gõ lẻ: của nó | Gõ chẵn: người sống] " + ("⚠ LẺ" if st["knocks"] % 2 else "CHẴN")
        opts = [Opt("mo_cua", "Mở cửa"), Opt("im_lang", "Im lặng, không mở")]
        if has("bua_ap_che"):
            opts.append(Opt("dan_bua", "Dán Bùa Áp Chế lên khung cửa", item="bua_ap_che"))
        return Scene(text, opts)

    def _advance(self, st, rng, step):
        st["round"] += 1
        if st["round"] > st["rounds"]:
            step.text += " Tiếng gõ ngưng hẳn. Hành lang trở lại yên tĩnh."
            step.outcome = "survive"
        else:
            st["knocks"] = rng.randint(1, 5)
        return step

    def act(self, st, opt, rng, p):
        odd = st["knocks"] % 2 == 1
        if opt == "dan_bua":
            return Step("Bùa dán lên khung cửa cháy xém. Tiếng gõ dừng lại.", "survive", bind_bonus=0.2)
        if opt == "mo_cua":
            if not odd:
                return self._advance(st, rng, Step("Một người sống ngã vào, run rẩy cảm ơn rồi nhét vào tay bạn mấy đồng.",
                                                   fx={"coins": 15, "hp": 5}))
            if st["shield"] > 0:
                st["shield"] -= 1
                return self._advance(st, rng, Step("Thứ ngoài cửa vươn tay vào, nhưng khiên bóng đẩy nó lùi."))
            st["strikes"] += 1
            if st["strikes"] >= 2:
                return Step("Cửa mở. Không ai còn thấy bạn nữa.", "death")
            return self._advance(st, rng, Step("Cửa mở ra: không có ai, chỉ có hơi lạnh tràn vào.",
                                               dmg={"hp": -20, "sanity": -12}))
        if opt == "im_lang":
            if odd:
                return self._advance(st, rng, Step("Bạn im lặng. Tiếng gõ lẻ dần xa."))
            return self._advance(st, rng, Step("Bạn im lặng. Phía sau cửa, một lời cầu cứu tắt dần.", dmg={"sanity": -5}))
        return Step("Bạn do dự.")

    def boost(self, st):
        st["strikes"] = max(0, st["strikes"] - 1)


# ---------------------------------------------------------------- Quỷ Vực: tìm neo trước khi hết không khí
DIRS = ["Bắc", "Đông", "Nam", "Tây"]


class QuyVuc(Mechanic):
    id = "quy_vuc"
    can_flee = False

    def start(self, rng):
        return {"air": 5, "anchor": rng.randint(0, 3), "shield": 0, "exact": 0, "probes": {}}

    def scene(self, st, known, has):
        text = f"Bạn đã ở trong quỷ vực. Không khí còn {st['air']}. Không có lối ra."
        for d, msg in st["probes"].items():
            text += f"\n- {DIRS[int(d)]}: {msg}"
        if st["exact"]:
            text += f"\nGương Nứt soi ra: neo nằm ở hướng {DIRS[st['anchor']]}."
        elif 0 in known:
            text += f"\n[Neo nằm trên trục {'Bắc-Nam' if st['anchor'] % 2 == 0 else 'Đông-Tây'}]"
        opts = [Opt(f"tham_do_{i}", f"Thăm dò hướng {DIRS[i]}", "Tốn 1 không khí") for i in range(4)]
        opts += [Opt(f"pha_neo_{i}", f"Phá neo hướng {DIRS[i]}", "Sai thì tốn 3 không khí") for i in range(4)]
        if has("guong_nut"):
            opts.append(Opt("soi_guong", "Soi Gương Nứt tìm neo", item="guong_nut"))
        return Scene(text, opts)

    def act(self, st, opt, rng, p):
        a = st["anchor"]
        if opt == "soi_guong":
            st["exact"] = 1
            return Step("Gương nứt phản chiếu một điểm sáng lạnh.", dmg={"sanity": -5})
        if opt.startswith("tham_do_"):
            d = int(opt[8:])
            near = min((d - a) % 4, (a - d) % 4)
            msg = ("hơi lạnh đặc quánh" if near == 0 else "lạnh nhẹ" if near == 1 else "yên tĩnh lạ thường")
            st["probes"][str(d)] = msg
            st["air"] -= 1
            if st["air"] <= 0:
                return Step("Không khí cạn. Quỷ vực khép lại quanh bạn.", "death")
            return Step(f"Hướng {DIRS[d]}: {msg}.")
        if opt.startswith("pha_neo_"):
            d = int(opt[8:])
            if d == a:
                return Step("Neo vỡ vụn. Quỷ vực sụp xuống như tấm màn rách.", "survive")
            if st["shield"] > 0:
                st["shield"] -= 1
                return Step("Neo không vỡ, nhưng khiên bóng chặn phản lực.", dmg={"sanity": -10})
            st["air"] -= 3
            if st["air"] <= 0:
                return Step("Không khí cạn. Quỷ vực khép lại quanh bạn.", "death")
            return Step("Neo không vỡ. Quỷ vực siết nhanh hơn.", dmg={"sanity": -10, "hp": -8})
        return Step("Bạn do dự.")

    def boost(self, st):
        st["air"] += 2


MECHANICS = {m.id: m for m in (QuyThu(), QuyAnh(), QuyNhan(), QuyQuanTai(), QuyMon(), QuyVuc())}
