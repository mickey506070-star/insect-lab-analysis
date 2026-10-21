import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 設定網頁標題與排版
st.set_page_config(page_title="農藥毒理與孵化實驗數據分析系統", layout="wide")

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
    
    # 清理欄位空白
    df.columns = [c.strip() for c in df.columns]
    
    st.subheader("📋 原始數據預覽")
    st.dataframe(df, use_container_width=True)

    # ------------------ 1. 孵化率實驗 ------------------
    if "1. 孵化率" in exp_type:
        req_cols = ["分組", "農藥濃度", "重複", "卵量", "蟲量"]
        if not all(col in df.columns for col in req_cols):
            st.error(f"⚠️ 欄位名稱不符！請確保表格中包含：{', '.join(req_cols)}")
        else:
            # 逐筆計算孵化率
            df["孵化率(%)"] = (df["蟲量"] / df["卵量"]) * 100
            
            # 分組彙整 Mean ± SD
            summary = df.groupby(["分組", "農藥濃度"]).agg(
                重複數=("重複", "count"),
                平均卵量=("卵量", "mean"),
                平均蟲量=("蟲量", "mean"),
                平均孵化率=("孵化率(%)", "mean"),
                標準差=("孵化率(%)", "std")
            ).reset_index().fillna(0)
            
            st.subheader("📊 統計結果彙整表 (Mean ± SD)")
            display_summary = summary.copy()
            display_summary["孵化率 (Mean ± SD)"] = display_summary.apply(
                lambda r: f"{r['平均孵化率']:.2f}% ± {r['標準差']:.2f}", axis=1
            )
            st.dataframe(display_summary, use_container_width=True)
            
            # 學術長條圖 (Publication style)
            st.subheader("📈 學術標準圖表 (Bar Chart with SD)")
            
            fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
            
            # 建立 X 標籤
            summary["label"] = summary["分組"].astype(str) + "\n(" + summary["農藥濃度"].astype(str) + "%)"
            x = np.arange(len(summary))
            
            bars = ax.bar(x, summary["平均孵化率"], yerr=summary["標準差"], capsize=5, 
                          color="#4A708B", edgecolor="black", linewidth=1.2, width=0.5)
            
            ax.set_xticks(x)
            ax.set_xticklabels(summary["label"], fontsize=10)
            ax.set_ylabel("Hatching Rate (%)", fontsize=12, fontweight='bold')
            ax.set_ylim(0, max(100, (summary["平均孵化率"] + summary["標準差"]).max() + 10))
            
            # 學術圖表無外側多餘線條
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            
            st.pyplot(fig)

    # ------------------ 2. 死亡率實驗 ------------------
    else:
        req_cols = ["分組", "農藥濃度", "重複", "活蟲數", "死蟲數"]
        if not all(col in df.columns for col in req_cols):
            st.error(f"⚠️ 欄位名稱不符！請確保表格中包含：{', '.join(req_cols)}")
        else:
            # 總蟲數與觀測死亡率
            df["總蟲數"] = df["活蟲數"] + df["死蟲數"]
            df["原始死亡率(%)"] = (df["死蟲數"] / df["總蟲數"]) * 100
            
            # 尋找對照組（農藥濃度為 0 的組）計算自然死亡率
            control_rows = df[df["農藥濃度"] == 0]
            if len(control_rows) == 0:
                st.warning("⚠️ 查無農藥濃度為 0 的組別，將無法使用 Abbott 公式計算校正死亡率，目前顯示原始死亡率。")
                control_mortality = 0
            else:
                control_mortality = control_rows["原始死亡率(%)"].mean()
                st.info(f"💡 偵測到對照組（濃度 0%），平均自然死亡率為：**{control_mortality:.2f}%**")

            # Abbott 校正死亡率計算: (Pt - Po) / (100 - Po) * 100
            if control_mortality < 100:
                df["校正死亡率(%)"] = df.apply(
                    lambda r: max(0, ((r["原始死亡率(%)"] - control_mortality) / (100 - control_mortality)) * 100),
                    axis=1
                )
            else:
                df["校正死亡率(%)"] = 0

            # 分組彙整
            summary = df.groupby(["分組", "農藥濃度"]).agg(
                重複數=("重複", "count"),
                平均活蟲=("活蟲數", "mean"),
                平均死蟲=("死蟲數", "mean"),
                平均原始死亡率=("原始死亡率(%)", "mean"),
                原始死亡率SD=("原始死亡率(%)", "std"),
                平均校正死亡率=("校正死亡率(%)", "mean"),
                校正死亡率SD=("校正死亡率(%)", "std")
            ).reset_index().fillna(0)
            
            st.subheader("📊 統計結果彙整表 (Mean ± SD)")
            display_summary = summary.copy()
            display_summary["校正死亡率 (Mean ± SD)"] = display_summary.apply(
                lambda r: f"{r['平均校正死亡率']:.2f}% ± {r['校正死亡率SD']:.2f}", axis=1
            )
            st.dataframe(display_summary, use_container_width=True)

            # 繪製學術圖表
            st.subheader("📈 學術標準圖表 (Abbott's Corrected Mortality)")
            
            fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
            summary["label"] = summary["分組"].astype(str) + "\n(" + summary["農藥濃度"].astype(str) + "%)"
            x = np.arange(len(summary))
            
            ax.bar(x, summary["平均校正死亡率"], yerr=summary["校正死亡率SD"], capsize=5, 
                   color="#8B3A3A", edgecolor="black", linewidth=1.2, width=0.5)
            
            ax.set_xticks(x)
            ax.set_xticklabels(summary["label"], fontsize=10)
            ax.set_ylabel("Corrected Mortality (%)", fontsize=12, fontweight='bold')
            ax.set_ylim(0, 105)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            
            st.pyplot(fig)
