# -*- coding: utf-8 -*-
"""
03_進階分析.py
政府開放資料應用案例（延伸）：A1類（死亡）道路交通事故資料長期趨勢分析
Stage 3：進階分析

畫四張圖：
  1) 地圖視覺化：全臺事故地點密度熱點圖（經緯度二維直方圖）
  2) 道路型態分析：各道路型態大類別事故件數比較
  3) 多因子交叉：道路型態 × 日夜（光線）交叉比較
  4) 多因子交叉：天候 × 光線 交叉比較，找出風險最高的組合

【執行前準備】
跟 01_資料探索.py、02_EDA探索圖表.py 一樣，本腳本要跟各年度的
「OO年度A1交通事故資料.csv」放在同一個資料夾。
"""

import csv
import glob
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load_all_rows():
    files = sorted(glob.glob("*A1交通事故資料*.csv"))
    if not files:
        raise FileNotFoundError(
            "找不到任何「OO年度A1交通事故資料.csv」，請確認腳本跟下載的年度CSV放在同一層資料夾"
        )
    rows = []
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if not r.get("發生年度", "").strip().isdigit():
                    continue
                rows.append(r)
    return rows


def accident_key(r):
    return (
        r.get("發生年度", "").strip(),
        r.get("發生月份", "").strip(),
        r.get("發生日期", "").strip(),
        r.get("發生時間", "").strip(),
        r.get("發生地點", "").strip(),
        r.get("經度", "").strip(),
        r.get("緯度", "").strip(),
    )


def dedup_accidents(rows):
    seen = set()
    result = []
    for r in rows:
        key = accident_key(r)
        if key in seen:
            continue
        seen.add(key)
        result.append(r)
    return result


def is_day(r):
    """把光線名稱簡化成「日間」/「夜間」二分類，供多因子交叉分析使用。
    日間自然光線、晨或暮光 → 日間；夜間有照明、夜間無照明 → 夜間。
    其餘無法判斷的回傳 None。"""
    light = r.get("光線名稱", "").strip()
    if light in ("日間自然光線", "晨或暮光"):
        return "日間"
    if light in ("夜間(或隧道、地下道、涵洞)有照明", "夜間(或隧道、地下道、涵洞)無照明"):
        return "夜間"
    return None


def valid_coords(accidents):
    """回傳(經度,緯度)有效清單，只保留落在臺灣合理範圍內的點"""
    pts = []
    for r in accidents:
        try:
            lon = float(r.get("經度", "").strip())
            lat = float(r.get("緯度", "").strip())
        except ValueError:
            continue
        if 118 <= lon <= 123 and 21 <= lat <= 26:
            pts.append((lon, lat))
    return pts


def chart1_geo_heatmap(accidents):
    """地圖視覺化：用經緯度二維直方圖畫出事故密度熱點（不依賴外部地圖圖磚，離線可畫）"""
    pts = valid_coords(accidents)
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]

    print(f"【圖1】地圖視覺化：可用經緯度座標 {len(pts)} 筆（總事故 {len(accidents)} 件）")

    fig, ax = plt.subplots(figsize=(7, 9))
    hb = ax.hexbin(lons, lats, gridsize=60, cmap="inferno", mincnt=1)
    ax.set_aspect("equal")
    ax.set_title("A1類（死亡）交通事故：全臺事故地點密度熱點圖", pad=16)
    ax.set_xlabel("經度")
    ax.set_ylabel("緯度")
    cb = fig.colorbar(hb, ax=ax, shrink=0.6)
    cb.set_label("事故件數（每格）")
    fig.tight_layout()
    fig.savefig("geo_heatmap.png", dpi=150)
    plt.close(fig)
    print("已輸出 geo_heatmap.png")


def chart2_road_type(accidents):
    """道路型態分析：各道路型態大類別事故件數比較"""
    road_counter = Counter(
        r.get("道路型態大類別名稱", "").strip() for r in accidents if r.get("道路型態大類別名稱", "").strip()
    )
    items = road_counter.most_common()
    labels = [w for w, _ in items]
    counts = [c for _, c in items]
    total = sum(counts)

    print("\n【圖2】道路型態大類別 事故件數：")
    for w, c in items:
        print(f"  {w}：{c} 件（{c / total * 100:.1f}%）")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.bar(labels, counts, color="#4A90A4")
    ax.set_title("A1類（死亡）交通事故：道路型態大類別比較", pad=16)
    ax.set_ylabel("事故件數")
    ax.set_ylim(top=max(counts) * 1.2)
    for i, c in enumerate(counts):
        ax.annotate(f"{c}\n({c / total * 100:.1f}%)", xy=(i, c), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("road_type.png", dpi=150)
    plt.close(fig)
    print("已輸出 road_type.png")


def chart3_road_type_daynight_cross(accidents):
    """
    多因子交叉：道路型態 × 日夜。
    看同一種道路型態下，夜間事故佔比是不是特別高（例如彎道夜間視線差風險可能更高）。
    只取樣本數夠多的道路型態類別，避免用個位數樣本畫圖誤導。
    """
    cross = defaultdict(lambda: Counter())
    for r in accidents:
        road = r.get("道路型態大類別名稱", "").strip()
        d = is_day(r)
        if not road or d is None:
            continue
        cross[road][d] += 1

    # 只挑總樣本數 >= 100 的道路型態，確保比例有意義
    roads = [r for r in cross if sum(cross[r].values()) >= 100]
    roads.sort(key=lambda r: sum(cross[r].values()), reverse=True)

    night_ratio = [cross[r]["夜間"] / sum(cross[r].values()) * 100 for r in roads]
    totals = [sum(cross[r].values()) for r in roads]

    print("\n【圖3】道路型態 × 日夜 交叉比較（只列樣本數>=100的類別）：")
    for r, n, t in zip(roads, night_ratio, totals):
        print(f"  {r}（共{t}件）：夜間佔比 {n:.1f}%")
    overall_night_ratio = sum(cross[r]["夜間"] for r in roads) / sum(totals) * 100
    print(f"→ 整體平均夜間佔比：{overall_night_ratio:.1f}%")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = ["#B5651D" if n > overall_night_ratio else "#4A90A4" for n in night_ratio]
    bars = ax.bar(roads, night_ratio, color=colors)
    ax.axhline(overall_night_ratio, color="gray", linestyle="--", linewidth=1, label="整體平均")
    ax.set_title("不同道路型態下，事故發生於「夜間」的比例", pad=16)
    ax.set_ylabel("夜間事故佔比（%）")
    ax.set_ylim(top=max(night_ratio) * 1.3)
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    for bar, n in zip(bars, night_ratio):
        ax.annotate(f"{n:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, n),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("road_type_daynight_cross.png", dpi=150)
    plt.close(fig)
    print("已輸出 road_type_daynight_cross.png")


def chart4_weather_light_cross(accidents):
    """
    多因子交叉：天候 × 光線，找出風險最高的組合。
    因為各組合樣本數差異極大（晴天白天樣本數遠多於雨天夜間無照明），
    這裡改用「該組合佔整體事故的比例」搭配「該組合內夜間無照明子項的佔比」
    兩個角度呈現，避免直接比較件數造成誤導。
    """
    combo_counter = Counter()
    for r in accidents:
        weather = r.get("天候名稱", "").strip()
        light = r.get("光線名稱", "").strip()
        if weather in ("晴", "陰", "雨") and light in (
            "日間自然光線", "夜間(或隧道、地下道、涵洞)有照明",
            "夜間(或隧道、地下道、涵洞)無照明", "晨或暮光",
        ):
            light_short = {
                "日間自然光線": "日間",
                "晨或暮光": "晨昏",
                "夜間(或隧道、地下道、涵洞)有照明": "夜間有照明",
                "夜間(或隧道、地下道、涵洞)無照明": "夜間無照明",
            }[light]
            combo_counter[(weather, light_short)] += 1

    total = sum(combo_counter.values())
    print(f"\n【圖4】天候 × 光線 交叉比較（總樣本 {total} 件，只列晴/陰/雨）：")
    for (w, l), c in combo_counter.most_common():
        print(f"  {w} × {l}：{c} 件（{c / total * 100:.1f}%）")

    # 找出「雨天 + 夜間無照明」這種高風險組合佔雨天事故的比例，跟晴天做對照
    rain_total = sum(c for (w, l), c in combo_counter.items() if w == "雨")
    rain_night_no_light = combo_counter.get(("雨", "夜間無照明"), 0)
    sunny_total = sum(c for (w, l), c in combo_counter.items() if w == "晴")
    sunny_night_no_light = combo_counter.get(("晴", "夜間無照明"), 0)
    if rain_total:
        print(f"→ 雨天事故中「夜間無照明」佔比：{rain_night_no_light / rain_total * 100:.1f}%")
    if sunny_total:
        print(f"→ 晴天事故中「夜間無照明」佔比：{sunny_night_no_light / sunny_total * 100:.1f}%")

    weathers = ["晴", "陰", "雨"]
    light_cats = ["日間", "晨昏", "夜間有照明", "夜間無照明"]
    colors_map = {"日間": "#4A90A4", "晨昏": "#8FBF9F", "夜間有照明": "#8B4A9C", "夜間無照明": "#B5651D"}

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bottom = np.zeros(len(weathers))
    for lc in light_cats:
        vals = np.array([
            combo_counter.get((w, lc), 0) / sum(combo_counter.get((w, x), 0) for x in light_cats) * 100
            if sum(combo_counter.get((w, x), 0) for x in light_cats) else 0
            for w in weathers
        ])
        ax.bar(weathers, vals, bottom=bottom, label=lc, color=colors_map[lc])
        for i, v in enumerate(vals):
            if v >= 3:
                ax.annotate(f"{v:.0f}%", xy=(i, bottom[i] + v / 2), ha="center", va="center",
                            fontsize=8, color="white")
        bottom += vals
    ax.set_title("天候 × 光線：各天候下的光線狀況組成", pad=16)
    ax.set_ylabel("佔該天候事故比例（%）")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, fontsize=8)
    fig.tight_layout()
    fig.savefig("weather_light_cross.png", dpi=150)
    plt.close(fig)
    print("已輸出 weather_light_cross.png")


def main():
    rows = load_all_rows()
    print(f"共讀取 {len(rows)} 列原始資料（含多當事者重複列，尚未去重複）")
    accidents = dedup_accidents(rows)
    print(f"去重複後事故件數：{len(accidents)} 件\n")

    chart1_geo_heatmap(accidents)
    chart2_road_type(accidents)
    chart3_road_type_daynight_cross(accidents)
    chart4_weather_light_cross(accidents)


if __name__ == "__main__":
    main()
