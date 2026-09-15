# -*- coding: utf-8 -*-
"""
01_資料探索.py
政府開放資料應用案例（延伸）：A1類（死亡）道路交通事故資料長期趨勢分析
Stage 1：資料探索

資料來源：警政署「XX年傷亡道路交通事故資料」，data.gov.tw，例如111年資料集編號161199。
每個年度各下載一份「OO年度A1交通事故資料.csv」，A1類 = 造成人員當場或24小時內死亡的事故。

【執行前準備】
請把本腳本，跟從data.gov.tw下載的每個年度A1交通事故CSV檔案
（檔名類似「111年度A1交通事故資料.csv」）放在同一個資料夾。
腳本會自動讀取資料夾內所有檔名含「A1交通事故資料」的CSV再合併，不需要自己合併檔案。

【重要】這份資料是以「當事者」為單位存的：一件事故如果有2個當事者（例如機車+汽車），
就會有2列資料，這2列的事故層級欄位（天候、道路型態、經緯度…）會完全相同，
只有當事者層級欄位（車種、性別、年齡…）不同。要算「事故件數」時，
必須先用（發生年度,發生月份,發生日期,發生時間,發生地點,經度,緯度）當唯一鍵去重複，
只保留第一筆，否則事故數會被當事者人數灌水膨脹。
"""

import csv
import glob
from collections import Counter


def load_all_rows():
    files = sorted(glob.glob("*A1交通事故資料*.csv"))
    if not files:
        raise FileNotFoundError(
            "找不到任何「OO年度A1交通事故資料.csv」，請確認腳本跟下載的年度CSV放在同一層資料夾"
        )

    rows = []
    per_file_count = {}
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            n = 0
            for r in reader:
                # 檔案尾端常附加「事故類別：A1類」「資料提供日期：...」等說明列，
                # 不是真正的事故資料，用「發生年度必須是純數字」過濾掉。
                if not r.get("發生年度", "").strip().isdigit():
                    continue
                rows.append(r)
                n += 1
            per_file_count[fp] = n
    return files, rows, per_file_count


def accident_key(r):
    """事故層級唯一鍵：同一事故的多個當事者列，這幾個欄位會完全相同"""
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
    """去重複，只保留每件事故的第一筆當事者列，回傳「事故層級」的資料"""
    seen = set()
    result = []
    for r in rows:
        key = accident_key(r)
        if key in seen:
            continue
        seen.add(key)
        result.append(r)
    return result


def main():
    files, rows, per_file_count = load_all_rows()

    print("=" * 50)
    print("【基本資訊】")
    print(f"讀取檔案數：{len(files)} 個（{', '.join(files)}）")
    print(f"合併後總列數（含多當事者重複列）：{len(rows)} 列")
    if rows:
        print(f"欄位數：{len(rows[0].keys())}")

    accidents = dedup_accidents(rows)
    print(f"去重複後事故件數：{len(accidents)} 件")
    print(f"平均每件事故當事者列數：{len(rows) / len(accidents):.2f}")

    print("\n" + "=" * 50)
    print("【各年度事故件數（去重複後）】")
    # 注意：發生年度欄位本身存的就是西元年（例如2022），不是民國年
    year_counter = Counter(r.get("發生年度", "").strip() for r in accidents)
    for year in sorted(year_counter):
        print(f"  {year}年（西元）：{year_counter[year]} 件")

    print("\n" + "=" * 50)
    print("【各檔案原始列數（尚未去重複，供對照）】")
    for fp, n in sorted(per_file_count.items()):
        print(f"  {fp}：{n} 列")

    print("\n" + "=" * 50)
    print("【天候名稱 分布（事故層級）】")
    weather_counter = Counter(r.get("天候名稱", "").strip() for r in accidents)
    for w, n in weather_counter.most_common():
        print(f"  {w!r}：{n} 件")

    print("\n" + "=" * 50)
    print("【光線名稱 分布（事故層級）】")
    light_counter = Counter(r.get("光線名稱", "").strip() for r in accidents)
    for l, n in light_counter.most_common():
        print(f"  {l!r}：{n} 件")

    print("\n" + "=" * 50)
    print("【道路型態大類別名稱 分布（事故層級）】")
    road_counter = Counter(r.get("道路型態大類別名稱", "").strip() for r in accidents)
    for road, n in road_counter.most_common():
        print(f"  {road!r}：{n} 件")

    print("\n" + "=" * 50)
    print("【事故位置大類別名稱 分布（事故層級，可用來看路口 vs 路段）】")
    loc_counter = Counter(r.get("事故位置大類別名稱", "").strip() for r in accidents)
    for loc, n in loc_counter.most_common():
        print(f"  {loc!r}：{n} 件")

    print("\n" + "=" * 50)
    print("【經緯度資料檢查】")
    valid_coord = 0
    invalid_coord = 0
    for r in accidents:
        try:
            lon = float(r.get("經度", "").strip())
            lat = float(r.get("緯度", "").strip())
            # 臺灣經緯度大致範圍
            if 118 <= lon <= 123 and 21 <= lat <= 26:
                valid_coord += 1
            else:
                invalid_coord += 1
        except ValueError:
            invalid_coord += 1
    print(f"經緯度落在臺灣合理範圍內：{valid_coord} 件")
    print(f"經緯度缺失或異常：{invalid_coord} 件")

    print("\n" + "=" * 50)
    print("【發生時間格式檢查（節錄前5筆）】")
    for r in accidents[:5]:
        print(f"  {r.get('發生時間', '')!r}")

    print("\n" + "=" * 50)
    print("【死亡受傷人數 欄位檢查（節錄前5筆）】")
    for r in accidents[:5]:
        print(f"  {r.get('死亡受傷人數', '')!r}")


if __name__ == "__main__":
    main()
