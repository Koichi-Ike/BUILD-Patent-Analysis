import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# タイトル
st.title("特許データ可視化ツール")

# ファイルアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is not None:
    # CSVファイルを読み込む
    data = pd.read_csv(uploaded_file)

    # 出願人/権利者列の処理
    applicants_column = '出願人/権利者'
    if applicants_column not in data.columns:
        st.error(f"'{applicants_column}' 列が見つかりません。適切なデータをアップロードしてください。")
    else:
        # 出願人/権利者列をカンマで分割し、すべての出願人を一つのリストにまとめる
        applicants_split = data[applicants_column].dropna().str.split(',')
        all_applicants = [applicant.strip() for sublist in applicants_split for applicant in sublist]

        # 出願人ごとの件数をカウント
        applicant_counts = pd.Series(all_applicants).value_counts()

        # 上位10出願人を取得
        top_10_applicants = applicant_counts.head(10)

        # サイドバーに出願人の選択・フィルタリングUIを追加
        st.sidebar.subheader("表示する出願人を選択")
        selected_applicants = st.sidebar.multiselect(
            "出願人を選択してください",
            options=applicant_counts.index,
            default=top_10_applicants.index
        )

        # フィルタリングされた出願人に基づいてデータを更新
        filtered_applicant_counts = applicant_counts[selected_applicants]

        # 出力1：横棒グラフの作成
        st.subheader("出願人別出願件数")
        fig1 = px.bar(filtered_applicant_counts.sort_values(), orientation='h', 
                      labels={'value':'出願件数', 'index':'出願人'}, title='出願人別出願件数')
        st.plotly_chart(fig1)

        # 出願年を年に変換
        data['出願年'] = pd.to_datetime(data['出願日'], errors='coerce').dt.year

        # 出願人/権利者ごとにカンマ区切りで分割されたデータを展開
        exploded_data = data.dropna(subset=[applicants_column])
        exploded_data[applicants_column] = exploded_data[applicants_column].str.split(',')
        exploded_data = exploded_data.explode(applicants_column).reset_index(drop=True)

        # 各出願人/権利者ごとの出願年別の件数をクロス表で集計
        pivot_table = pd.pivot_table(exploded_data, values='文献番号', index=applicants_column, columns='出願年', aggfunc='count', fill_value=0)

        # フィルタリングされた出願人のみに絞り込み
        filtered_pivot = pivot_table.loc[selected_applicants]

        # 出願年は最新10年間分のみ表示
        filtered_pivot = filtered_pivot.iloc[:, -10:]

        # 出力2：ヒートチャートの作成（暖色系）
        st.subheader("選択した出願人の年間出願件数ヒートチャート")

        fig2 = px.imshow(
            filtered_pivot,
            labels={'x': '出願年', 'y': '出願人', 'color': '出願件数'},
            x=filtered_pivot.columns,
            y=filtered_pivot.index,
            color_continuous_scale='Reds',
            aspect='auto',
            title='選択した出願人の年間出願件数ヒートチャート'
        )

        fig2.update_layout(
            xaxis_title='出願年',
            yaxis_title='出願人',
            yaxis_autorange='reversed'
        )

        st.plotly_chart(fig2)

        # 直近3年間の出願件数を計算
        recent_years = filtered_pivot.columns[-3:]
        total_applications_recent_3_years = filtered_pivot[recent_years].sum(axis=1)

        # 全期間の合計出願件数を計算
        total_applications_all_years = filtered_pivot.sum(axis=1)

        # 直近3年間の出願割合を計算
        recent_3_year_ratio = total_applications_recent_3_years / total_applications_all_years

        # 出力3：バブルチャートの作成
        st.subheader("選択した出願人のバブルチャート")
        fig3 = go.Figure()

        fig3.add_trace(go.Scatter(
            x=recent_3_year_ratio, 
            y=total_applications_recent_3_years,
            mode='markers+text',
            text=filtered_pivot.index,
            marker=dict(size=total_applications_all_years, sizemode='area', sizeref=2.*max(total_applications_all_years)/(40.**2), sizemin=4),
            textposition="bottom center"
        ))

        fig3.update_layout(title='選択した出願人のバブルチャート',
                           xaxis_title='直近3年間の出願割合',
                           yaxis_title='直近3年間の出願件数')
        st.plotly_chart(fig3)

        # 文献情報表示用の出願人選択
        st.sidebar.subheader("文献情報を表示する出願人を選択")
        selected_applicant_for_docs = st.sidebar.selectbox(
            "文献情報を表示する出願人を選択してください",
            options=selected_applicants
        )

        # 選択された出願人の文献情報を表示
        st.subheader(f"{selected_applicant_for_docs}の文献情報一覧")
        docs_info = exploded_data[exploded_data[applicants_column] == selected_applicant_for_docs][['文献番号', '出願日', '発明の名称', 'ステージ', '文献URL']]

        if len(docs_info) > 0:
            # 文献番号にリンクを追加
            docs_info['文献番号'] = docs_info.apply(
                lambda row: f'<a href="{row["文献URL"]}" target="_blank">{row["文献番号"]}</a>', axis=1
            )

            # HTML形式で文献情報を表示（文献URLは表示しない）
            st.write(docs_info[['文献番号', '出願日', '発明の名称', 'ステージ']].to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.write("該当する文献情報はありません。")
