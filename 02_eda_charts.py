# -*- coding: utf-8 -*-
"""
02_EDA探索圖表.py
政府開放資料應用案例（延伸）：A1類（死亡）道路交通事故資料長期趨勢分析
Stage 2：EDA探索圖表

畫五張圖：
  1) 各年度事故件數趨勢
  2) 24小時各時段事故件數分布
  3) 天候別事故件數比較
  4) 天候 × 事故位置（路段/路口）交叉比較（堆疊比例圖）
  5) 光線狀況比較（白天 vs 夜間有/無照明）

【執行前準備】
跟 01_資料探索.py 一樣，本腳本要跟各年度的「OO年度A1交通事故資料.csv」放在同一個資料夾。
"""

import csv
import glob
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def parse_hour(t):
    """發生時間格式為6碼 HHMMSS（例如 '023000'），取前2碼當小時"""
    t = t.strip()
    if len(t) < 2 or not t[:2].isdigit():
        return None
    h = int(t[:2])
    if 0 <= h <= 23:
        return h
    return None


def chart1_year_trend(accidents):
    """各年度事故件數趨勢"""
    year_counter = Counter(r.get("發生年度", "").strip() for r in accidents)
    years = sorted(year_counter, key=lambda y: int(y))
    counts = [year_counter[y] for y in years]

    print("【圖1】各年度事故件數：")
    for y, c in zip(years, counts):
        print(f"  {y}年：{c} 件")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(years, counts, color="#B5651D")
    ax.set_title("A1類（死亡）交通事故：各年度件數趨勢", pad=16)
    ax.set_xlabel("年度（西元）")
    ax.set_ylabel("事故件數")
    ax.set_ylim(top=max(counts) * 1.2)
    for bar, c in zip(bars, counts):
        ax.annotate(f"{c}", xy=(bar.get_x() + bar.get_width() / 2, c),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("year_trend.png", dpi=150)
    plt.close(fig)
    print("已輸出 year_trend.png")


def chart2_hour_distribution(accidents):
    """24小時各時段事故件數分布"""
    hour_counter = Counter()
    skipped = 0
    for r in accidents:
        h = parse_hour(r.get("發生時間", ""))
        if h is None:
            skipped += 1
            continue
        hour_counter[h] += 1

    hours = list(range(24))
    counts = [hour_counter.get(h, 0) for h in hours]

    print(f"\n【圖2】24小時事故件數分布（無法解析時間的筆數：{skipped}）：")
    for h, c in zip(hours, counts):
        print(f"  {h:02d}時：{c} 件")
    peak_hour = hours[counts.index(max(counts))]
    print(f"→ 事故最集中的時段：{peak_hour:02d}時（{max(counts)}件）")

    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors = ["#8B4A9C" if c == max(counts) else "#4A90A4" for c in counts]
    bars = ax.bar([f"{h:02d}" for h in hours], counts, color=colors)
    ax.set_title("A1類（死亡）交通事故：24小時各時段事故件數分布", pad=16)
    ax.set_xlabel("發生時段（24小時制）")
    ax.set_ylabel("事故件數")
    ax.set_ylim(top=max(counts) * 1.25)
    for bar, c in zip(bars, counts):
        ax.annotate(f"{c}", xy=(bar.get_x() + bar.get_width() / 2, c),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("hour_distribution.png", dpi=150)
    plt.close(fig)
    print("已輸出 hour_distribution.png")


def chart3_weather_comparison(accidents):
    """天候別事故件數比較"""
    weather_counter = Counter(r.get("天候名稱", "").strip() for r in accidents if r.get("天候名稱", "").strip())
    items = weather_counter.most_common()
    labels = [w for w, _ in items]
    counts = [c for _, c in items]

    print("\n【圖3】天候別事故件數：")
    for w, c in items:
        print(f"  {w}：{c} 件")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.bar(labels, counts, color="#4A90A4")
    ax.set_title("A1類（死亡）交通事故：天候別事故件數", pad=16)
    ax.set_ylabel("事故件數")
    ax.set_yscale("log")
    ax.set_ylabel("事故件數（對數尺度，因晴天筆數遠多於其他天候）")
    for i, c in enumerate(counts):
        ax.annotate(f"{c}", xy=(i, c), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig("weather_comparison.png", dpi=150)
    plt.close(fig)
    print("已輸出 weather_comparison.png")


def chart4_weather_location_cross(accidents):
    """
    天候 × 事故位置（路段/路口）交叉比較。
    因為晴天事故本來就佔絕大多數，直接比「件數」會被晴天蓋過，
    所以改看「同一天候下，路口事故佔比是多少」，才能比較不同天候的路口風險是否更高。
    只取「路段」與「交叉路口」兩大類，其餘（其他、交流道）樣本太少不列入比較。
    """
    cross = defaultdict(lambda: Counter())
    for r in accidents:
        weather = r.get("天候名稱", "").strip()
        loc = r.get("事故位置大類別名稱", "").strip()
        if not weather or loc not in ("路段", "交叉路口"):
            continue
        cross[weather][loc] += 1

    # 只挑樣本數夠多的天候類別（晴、陰、雨），避免用個位數樣本畫圖誤導
    weathers = [w for w in ["晴", "陰", "雨"] if w in cross]
    segment_counts = [cross[w]["路段"] for w in weathers]
    junction_counts = [cross[w]["交叉路口"] for w in weathers]
    junction_ratio = [
        cross[w]["交叉路口"] / (cross[w]["路段"] + cross[w]["交叉路口"]) * 100
        for w in weathers
    ]

    print("\n【圖4】天候 × 事故位置 交叉比較（只列晴/陰/雨，樣本數足夠）：")
    for w, seg, jun, ratio in zip(weathers, segment_counts, junction_counts, junction_ratio):
        print(f"  {w}：路段 {seg} 件、交叉路口 {jun} 件，路口佔比 {ratio:.1f}%")

    fig, ax = plt.subplots(figsize=(7, 5.5))
    bars = ax.bar(weathers, junction_ratio, color="#B5651D")
    ax.axhline(sum(junction_counts) / (sum(segment_counts) + sum(junction_counts)) * 100,
               color="gray", linestyle="--", linewidth=1, label="三種天候整體平均")
    ax.set_title("不同天候下，事故發生於「交叉路口」的比例", pad=16)
    ax.set_ylabel("交叉路口事故佔比（%）")
    ax.set_ylim(top=max(junction_ratio) * 1.3)
    ax.legend()
    for bar, r in zip(bars, junction_ratio):
        ax.annotate(f"{r:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, r),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("weather_location_cross.png", dpi=150)
    plt.close(fig)
    print("已輸出 weather_location_cross.png")


def chart5_light_comparison(accidents):
    """光線狀況比較"""
    light_counter = Counter(r.get("光線名稱", "").strip() for r in accidents if r.get("光線名稱", "").strip())
    items = light_counter.most_common()
    labels = [l for l, _ in items]
    counts = [c for _, c in items]
    total = sum(counts)

    print("\n【圖5】光線狀況比較：")
    for l, c in items:
        print(f"  {l}：{c} 件（{c / total * 100:.1f}%）")

    night_no_light = light_counter.get("夜間(或隧道、地下道、涵洞)無照明", 0)
    night_with_light = light_counter.get("夜間(或隧道、地下道、涵洞)有照明", 0)
    print(f"→ 夜間無照明佔全部夜間事故的比例："
          f"{night_no_light / (night_no_light + night_with_light) * 100:.1f}%"
          f"（夜間無照明 {night_no_light} 件 / 夜間合計 {night_no_light + night_with_light} 件）")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = ["#4A90A4" if "日間" in l or "暮光" in l else "#8B4A9C" for l in labels]
    bars = ax.barh(labels, counts, color=colors)
    ax.invert_yaxis()
    ax.set_title("A1類（死亡）交通事故：光線狀況比較", pad=16)
    ax.set_xlabel("事故件數")
    for i, c in enumerate(counts):
        ax.annotate(f"{c}（{c / total * 100:.1f}%）", xy=(c, i), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig("light_comparison.png", dpi=150)
    plt.close(fig)
    print("已輸出 light_comparison.png")


def main():
    rows = load_all_rows()
    print(f"共讀取 {len(rows)} 列原始資料（含多當事者重複列，尚未去重複）")
    accidents = dedup_accidents(rows)
    print(f"去重複後事故件數：{len(accidents)} 件\n")

    chart1_year_trend(accidents)
    chart2_hour_distribution(accidents)
    chart3_weather_comparison(accidents)
    chart4_weather_location_cross(accidents)
    chart5_light_comparison(accidents)


if __name__ == "__main__":
    main()
