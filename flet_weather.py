import flet
from flet import (Page, Text, TextField, ElevatedButton, Column, Row, ListView, ListTile, ProgressRing, AppBar, IconButton, Icon, Container, Card, Divider, icons)
import requests
import threading
from datetime import datetime
import time

AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"


def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def weather_to_emoji(text: str) -> str:
    if not text:
        return "❓"
    # simple heuristics for Japanese weather strings
    if "晴" in text:
        return "☀️"
    if "雨" in text or "降" in text:
        return "🌧️"
    if "雪" in text:
        return "❄️"
    if "曇" in text or "くも" in text:
        return "☁️"
    if "雷" in text or "かみなり" in text:
        return "⚡️"
    return "🌈"


class WeatherApp:
    def __init__(self, page: Page):
        self.page = page
        page.title = "天気予報アプリ (気象庁 API)"
        page.horizontal_alignment = "stretch"

        self.search = TextField(label="検索（地域名でフィルタ）", expand=True)
        self.search.on_change = self.on_search_change

        self.list_view = ListView(expand=True, spacing=5)
        self.list_loading = ProgressRing()

        # state for UI polish
        self.selected_code = None
        self.forecast_cache = {}
        self.last_update_text = Text("")

        # App bar with refresh and last update
        page.appbar = AppBar(title=Text("天気予報 (気象庁API)"),
                             actions=[IconButton(icons.Icons.REFRESH, on_click=lambda e: page.run_thread(self.load_areas)),
                                      self.last_update_text])

        left = Column([
            Row([self.search, IconButton(icons.Icons.SEARCH_ROUNDED, on_click=self.on_search_click)]),
            Container(self.list_view, width=360, padding=10),
        ], width=360)

        self.detail_content = Column([Text("地域を選択してください")], expand=True)
        self.detail = Card(content=Container(self.detail_content, padding=10), expand=True)

        page.add(Row([left, self.detail], alignment="spaceBetween"))

        # load area list in background (use page's thread runner)
        page.run_thread(self.load_areas)

    def on_search_click(self, e):
        self.filter_list()

    def on_search_change(self, e):
        self.filter_list()

    def load_areas(self):
        # show loading
        self.areas = []
        self.list_view.controls.clear()
        self.list_view.controls.append(self.list_loading)
        self.page.schedule_update()

        data = fetch_json(AREA_URL)
        if data is None or isinstance(data, dict) and data.get("error"):
            self.page.controls.append(Text(f"地域リストの取得に失敗: {data.get('error')}"))
            self.page.update()
            return

        offices = data.get("offices", {})
        # store as list of tuples (code, name)
        self.areas = [(code, info.get("name", "")) for code, info in offices.items()]
        self.areas.sort(key=lambda x: x[1])
        self.populate_list()

    def populate_list(self):
        self.list_view.controls.clear()
        for code, name in self.areas:
            selected_bg = "#e8f2ff" if code == self.selected_code else None
            item = ListTile(title=Text(name, weight="bold"),
                            subtitle=Text(code, size=12, color="#666"),
                            leading=Icon(icons.Icons.LOCATION_ON),
                            on_click=lambda e, c=code, n=name: self.on_area_selected(c, n))
            self.list_view.controls.append(Container(item, padding=6, bgcolor=selected_bg, border_radius=6))
        self.page.schedule_update()

    def filter_list(self):
        q = self.search.value.strip().lower()
        self.list_view.controls.clear()
        for code, name in self.areas:
            if q and q not in name.lower():
                continue
            btn = ElevatedButton(f"{name} ({code})", on_click=lambda e, c=code, n=name: self.on_area_selected(c, n))
            self.list_view.controls.append(btn)
        self.page.update()

    def on_area_selected(self, code, name):
        # remember selection and refresh list highlight
        self.selected_code = code
        self.populate_list()

        # clear detail and show loading
        self.detail_content.controls.clear()
        self.detail_content.controls.append(Text(f"{name} を取得中..."))
        self.page.schedule_update()
        # run forecast loading in page executor
        self.page.run_thread(self.load_forecast, code, name)

    def load_forecast(self, code, name):
        # use cache for a short time (10 minutes)
        now = time.time()
        cached = self.forecast_cache.get(code)
        if cached and now - cached[1] < 600:
            report = cached[0]
            self.show_forecast(report, name)
            # update last_update_text but don't change fetched time
            self.last_update_text.value = f"最終取得: {datetime.fromtimestamp(cached[1]).strftime('%H:%M:%S')}"
            self.page.schedule_update()
            return

        url = FORECAST_URL.format(code=code)
        data = fetch_json(url)
        if data is None or isinstance(data, dict) and data.get("error"):
            self.show_error(data.get('error'))
            self.page.schedule_update()
            return
        # data is a list, typically first element contains report
        report = data[0] if isinstance(data, list) and len(data) > 0 else None
        if not report:
            self.show_error("予報データが見つかりません")
            self.page.schedule_update()
            return
        # cache and display
        self.forecast_cache[code] = (report, time.time())
        self.last_update_text.value = f"最終取得: {datetime.now().strftime('%H:%M:%S')}"
        self.show_forecast(report, name)
        self.page.schedule_update()


    def show_error(self, msg):
        self.detail_content.controls.clear()
        self.detail_content.controls.append(Container(Text(f"エラー: {msg}", color='red'), padding=10))
        self.page.schedule_update()

    def show_forecast(self, report, name):
        self.detail_content.controls.clear()
        office = report.get("publishingOffice", "不明")
        report_time = report.get("reportDatetime", "")
        header = Column([
            Text(f"{name} の予報", size=20, weight="bold"),
            Text(f"発表: {office}  {report_time}", size=12, color="#666666"),
        ], tight=True)
        self.detail_content.controls.append(Card(content=Container(header, padding=10)))

        time_series = report.get("timeSeries", [])
        if time_series:
            weather_ts = time_series[0]
            dates = weather_ts.get("timeDefines", [])
            areas = weather_ts.get("areas", [])
            if areas:
                area0 = areas[0]
                weathers = area0.get("weathers", [])
                for i, d in enumerate(dates):
                    w = weathers[i] if i < len(weathers) else "-"
                    emoji = weather_to_emoji(w)
                    row = Row([Text(d, size=12, color="#333"), Text(emoji, size=20), Text(w)], alignment="spaceBetween")
                    self.detail_content.controls.append(Container(row, padding=6))
                    self.detail_content.controls.append(Divider())
        self.page.schedule_update()


def main(page: Page):
    WeatherApp(page)


if __name__ == "__main__":
    # Launch as a desktop application (not web browser)
    flet.run(main, view=flet.AppView.FLET_APP)
