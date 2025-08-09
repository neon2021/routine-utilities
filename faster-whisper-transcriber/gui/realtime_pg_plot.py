# 文件名：realtime_pg_plot.py
import sys
import psycopg2
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer
import pyqtgraph as pg

from global_config.config import yaml_config_boxed
from global_config.logger_config import logger

# 数据库连接配置
DB_CONFIGS = {
    "postgres": {
        "dbname": yaml_config_boxed.gui.postgres.dbname,
        "user": yaml_config_boxed.gui.postgres.user,
        "password": yaml_config_boxed.gui.postgres.password,
        "host": yaml_config_boxed.gui.postgres.host,
        "port": 5432
    },
    "ubuntu_postgres": {
        "dbname": yaml_config_boxed.gui.ubuntu_postgres.dbname,
        "user": yaml_config_boxed.gui.ubuntu_postgres.user,
        "password": yaml_config_boxed.gui.ubuntu_postgres.password,
        "host": yaml_config_boxed.gui.ubuntu_postgres.host,
        "port": 5432
    }
}

# === 查询语句配置 ===
TABLE_QUERIES = {
    "file_inventory": {
        "field": "scanned_at",
        "sql": "SELECT DATE_TRUNC('minute', scanned_at) as ts, COUNT(*) FROM file_inventory GROUP BY ts ORDER BY ts"
    },
    "transcription_log": {
        "field": "ended_at",
        "sql": "SELECT DATE_TRUNC('minute', ended_at) as ts, COUNT(*) FROM transcription_log GROUP BY ts ORDER BY ts"
    }
}

class MonitorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 PostgreSQL 实时监控")

        self.layout = QVBoxLayout()
        self.status_label = QLabel("🔄 最近更新时间：--")
        self.layout.addWidget(self.status_label)

        self.plots = {}
        self.plot_widgets = {}

        for db_name in DB_CONFIGS:
            for table in TABLE_QUERIES:
                plot_title = f"{db_name}.{table}"
                self.layout.addWidget(QLabel(f"📊 {plot_title}"))

                pw = pg.PlotWidget()
                pw.setLabel("left", "数量")
                pw.setLabel("bottom", "时间（分钟）")
                pw.showGrid(x=True, y=True)
                self.layout.addWidget(pw)

                self.plot_widgets[plot_title] = pw
                self.plots[plot_title] = pw.plot([], [])

        self.setLayout(self.layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(5000)  # 每 5 秒刷新
        self.update_all()

    def update_all(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.setText(f"🔄 最近更新时间：{now}")

        for db, config in DB_CONFIGS.items():
            try:
                conn = psycopg2.connect(**config)
                for table, cfg in TABLE_QUERIES.items():
                    query = cfg["sql"]
                    df = pd.read_sql(query, conn)
                    logger.info(f"table:{table}, df:{df}")
                    if not df.empty:
                        x = pd.to_datetime(df['ts'])
                        y = df['count']
                        x_unix = x.astype("int64") // 10**9
                        plot_key = f"{db}.{table}"

                        self.plot_widgets[plot_key].clear()
                        self.plots[plot_key] = self.plot_widgets[plot_key].plot(
                            x=x_unix,
                            y=y,
                            pen=pg.mkPen(color="c", width=2)
                        )
                        # 设置X轴时间标签
                        self.plot_widgets[plot_key].getAxis("bottom").setTicks([
                            [(v, pd.to_datetime(v, unit="s").strftime("%H:%M")) for v in x_unix]
                        ])
                conn.close()
            except Exception as e:
                print(f"[ERROR] {db} - {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MonitorApp()
    window.resize(1000, 800)
    window.show()
    sys.exit(app.exec_())