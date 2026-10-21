import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="農藥毒理與孵化實驗分析系統", layout="wide")

st.title("🔬 昆蟲農藥毒理與孵化實驗分析系統")
st.caption("支援手機與電腦瀏覽｜自動計算孵化率、死亡率、Abbott校正死亡率、Mean ± SD｜產出學術圖表")

# 側邊欄選擇實驗類型
exp_type = st.sidebar.selectbox("請選擇實驗類型", ["1. 孵化率實驗 (Hatching Rate)", "2. 死亡率實驗 (Mortality Rate)"])

st.sidebar.markdown("---")
st.sidebar.info("💡 **Excel 欄位格式說明**：\n"
                 "- **孵化實驗**需包含：`分組`, `農藥濃度`, `重複`, `卵量`, `蟲量`\n"
                 "- **死亡實驗**需包含：`分組`, `農藥濃度`, `重複`, `活蟲數`, `死蟲數`")

uploaded_file = st.file_uploader("請上傳 Excel 檔案 (.xlsx) 或 CSV 檔案", type=["xlsx", "csv"])

if uploaded_file:
    # 讀取檔案
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    st.subheader("📋 原始數據預覽")
    st.dataframe(df, use_container_width=True)

    # ------------------ 1. 孵化率實驗 ------------------
    if "1. 孵化率" in exp_type:
        req_cols = ["分組", "農藥濃度", "重複", "卵量", "蟲量"]
        if not all(col in df.columns for col in req_cols):
            st.error(f"⚠️ 欄位名稱不符！請確保表格中包含：{', '.join(req_cols)}")
        else:
            df["孵化率(%)"] = (df["蟲量"] / df["卵量"]) * 100
            
            summary = df.groupby(["分組", "農藥濃度"]).agg(
                重複數=("重複", "count"),
                平均卵量=("卵量", "mean"),
                平均蟲量=("蟲量", "mean"),
                平均孵化率=("孵化率(%)", "mean"),
                標準差=("孵化率(%)", "std")
            ).reset_index().fillna(0)
            
            summary["誤差上限"] = summary["平均孵化率"] + summary["標準差"]
            summary["誤差下限"] = (summary["平均孵化率"] - summary["標準差"]).clip(lower=0)
            summary["組別標籤"] = summary["分組"].astype(str) + " (" + summary["農藥濃度"].astype(str) + "%)"
            
            st.subheader("📊 統計結果彙整表 (Mean ± SD)")
            display_summary = summary.copy()
            display_summary["孵化率 (Mean ± SD)"] = display_summary.apply(
                lambda r: f"{r['平均孵化率']:.2f}% ± {r['標準差']:.2f}", axis=1
            )
            st.dataframe(display_summary[["分組", "農藥濃度", "重複數", "平均卵量", "平均蟲量", "孵化率 (Mean ± SD)"]], use_container_width=True)
            
            st.subheader("📈 學術標準長條圖 (Mean ± SD)")
            bars = alt.Chart(summary).mark_bar(color="#4A708B", size=40).encode(
                x=alt.X("組別標籤:N", title="實驗組別 (濃度)", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("平均孵化率:Q", title="Hatching Rate (%)", scale=alt.Scale(domain=[0, 105]))
            )
            error_bars = alt.Chart(summary).mark_errorbar(extent='stderr', color="black").encode(
                x=alt.X("組別標籤:N"),
                y=alt.Y("誤差下限:Q"),
                y2="誤差上限:Q"
            )
            chart = (bars + error_bars).properties(height=350)
            st.altair_chart(chart, use_container_width=True)

    # ------------------ 2. 死亡率實驗 ------------------
    else:
        req_cols = ["分組", "農藥濃度", "重複", "活蟲數", "死蟲數"]
        if not all(col in df.columns for col in req_cols):
            st.error(f"⚠️ 欄位名稱不符！請確保表格中包含：{', '.join(req_cols)}")
        else:
            df["總蟲數"] = df["活蟲數"] + df["死蟲數"]
            df["原始死亡率(%)"] = (df["死蟲數"] / df["總蟲數"]) * 100
            
            control_rows = df[df["農藥濃度"] == 0]
            if len(control_rows) == 0:
                st.warning("⚠️ 查無農藥濃度為 0 的組別，將以原始死亡率呈現。")
                control_mortality = 0
            else:
                control_mortality = control_rows["原始死亡率(%)"].mean()
                st.info(f"💡 偵測到對照組（濃度 0%），平均自然死亡率為：**{control_mortality:.2f}%**")

            # Abbott's 公式
            if control_mortality < 100:
                df["校正死亡率(%)"] = df.apply(
                    lambda r: max(0, ((r["原始死亡率(%)"] - control_mortality) / (100 - control_mortality)) * 100),
                    axis=1
                )
            else:
                df["校正死亡率(%)"] = 0

            summary = df.groupby(["分組", "農藥濃度"]).agg(
                重複數=("重複", "count"),
                平均活蟲=("活蟲數", "mean"),
                平均死蟲=("死蟲數", "mean"),
                平均原始死亡率=("原始死亡率(%)", "mean"),
                原始死亡率SD=("原始死亡率(%)", "std"),
                平均校正死亡率=("校正死亡率(%)", "mean"),
                校正死亡率SD=("校正死亡率(%)", "std")
            ).reset_index().fillna(0)
            
            summary["誤差上限"] = (summary["平均校正死亡率"] + summary["校正死亡率SD"]).clip(upper=100)
            summary["誤差下限"] = (summary["平均校正死亡率"] - summary["校正死亡率SD"]).clip(lower=0)
            summary["組別標籤"] = summary["分組"].astype(str) + " (" + summary["農藥濃度"].astype(str) + "%)"
            
            st.subheader("📊 統計結果彙整表 (Mean ± SD)")
            display_summary = summary.copy()
            display_summary["校正死亡率 (Mean ± SD)"] = display_summary.apply(
                lambda r: f"{r['平均校正死亡率']:.2f}% ± {r['校正死亡率SD']:.2f}", axis=1
            )
            st.dataframe(display_summary[["分組", "農藥濃度", "重複數", "平均活蟲", "平均死蟲", "校正死亡率 (Mean ± SD)"]], use_container_width=True)

            st.subheader("📈 學術標準長條圖 (Abbott's Corrected Mortality ± SD)")
            bars = alt.Chart(summary).mark_bar(color="#8B3A3A", size=40).encode(
                x=alt.X("組別標籤:N", title="實驗組別 (濃度)", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("平均校正死亡率:Q", title="Corrected Mortality (%)", scale=alt.Scale(domain=[0, 105]))
            )
            error_bars = alt.Chart(summary).mark_errorbar(extent='stderr', color="black").encode(
                x=alt.X("組別標籤:N"),
                y=alt.Y("誤差下限:Q"),
                y2="誤差上限:Q"
            )
            chart = (bars + error_bars).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
