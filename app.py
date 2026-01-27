import flet as ft
import sqlite3

def main(page: ft.Page):
    # ==========================================
    # アプリの基本設定
    # ==========================================
    page.title = "木更津市 賃貸検索アプリ"
    page.theme_mode = ft.ThemeMode.LIGHT
    # 最新のFletでは window_width ではなく window.width を推奨
    page.window.width = 1000
    page.window.height = 800
    page.padding = 20

    # ==========================================
    # 1. データベースからデータを取る関数
    # ==========================================
    def get_data_from_db(keyword=""):
        # 【修正】先ほど作成したDB名 'saishukadai.db' に合わせました
        conn = sqlite3.connect('saishukadai.db')
        cur = conn.cursor()
        
        if keyword:
            # 駅名や物件名であいまい検索
            query = """
                SELECT name, station, price, age, floor_plan 
                FROM properties 
                WHERE station LIKE ? OR name LIKE ?
            """
            cur.execute(query, (f'%{keyword}%', f'%{keyword}%'))
        else:
            # キーワードがない場合は全件（上限100件）表示
            cur.execute("SELECT name, station, price, age, floor_plan FROM properties LIMIT 100")
            
        rows = cur.fetchall()
        conn.close()
        return rows

    # ==========================================
    # 2. データを画面の「表」に変換する関数
    # ==========================================
    def create_table_rows(data):
        rows = []
        for row in data:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row[0], size=12, weight="bold")), # 物件名
                        ft.DataCell(ft.Text(row[1], size=12)),                # 駅
                        ft.DataCell(ft.Text(f"{row[2]:,}円", color="blue")),  # 家賃
                        ft.DataCell(ft.Text(f"築{row[3]}年")),                # 築年数
                        ft.DataCell(ft.Text(row[4])),                         # 間取り
                    ]
                )
            )
        return rows

    # ==========================================
    # 3. 画面パーツ（UI）の作成
    # ==========================================
    title_text = ft.Text("木更津市 賃貸データ分析ダッシュボード", size=24, weight="bold", color="teal")
    status_text = ft.Text("データを読み込み中...", color="grey")

    # データテーブルの設定
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("物件名")),
            ft.DataColumn(ft.Text("最寄駅")),
            ft.DataColumn(ft.Text("家賃"), numeric=True),
            ft.DataColumn(ft.Text("築年数"), numeric=True),
            ft.DataColumn(ft.Text("間取り")),
        ],
        rows=[],
        border=ft.border.all(1, "grey"),
        vertical_lines=ft.border.BorderSide(1, "grey"),
        heading_row_color="blueGrey50", 
        # expand=True は Column の中に入れる場合、scroll設定と競合することがあるので注意
    )

    # ==========================================
    # 4. イベント処理
    # ==========================================
    def search_click(e):
        keyword = search_field.value
        results = get_data_from_db(keyword)
        
        # データを更新
        data_table.rows = create_table_rows(results)
        
        if len(results) == 0:
            status_text.value = "データが見つかりませんでした。"
            status_text.color = "red"
        else:
            status_text.value = f"検索結果: {len(results)} 件"
            status_text.color = "black"
            
        page.update()

    # 検索窓とボタン
    search_field = ft.TextField(
        label="駅名や物件名で検索（例: 木更津）", 
        width=400, 
        prefix_icon="search", 
        on_submit=search_click
    )
    
    search_button = ft.ElevatedButton(content=ft.Text("検索"), on_click=search_click)

    # ==========================================
    # 5. 初期表示処理とレイアウト
    # ==========================================
    initial_data = get_data_from_db()
    data_table.rows = create_table_rows(initial_data)
    status_text.value = f"全データ表示中（最新{len(initial_data)}件）"

    # 画面に追加
    page.add(
        ft.Column([
            title_text,
            ft.Divider(),
            ft.Row([search_field, search_button], alignment="center"),
            status_text,
            # テーブルをスクロール可能にするためのコンテナ
            ft.Container(
                content=ft.Column([data_table], scroll=ft.ScrollMode.AUTO),
                height=500, # 高さを指定しないとスクロールしない場合があります
                border=ft.border.all(1, "grey50"),
                border_radius=10,
                padding=10
            )
        ])
    )

if __name__ == "__main__":
    ft.app(target=main)