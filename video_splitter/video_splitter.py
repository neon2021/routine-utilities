import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog,
                           QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSpinBox,
                           QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt
from functools import partial
import ffmpeg
import subprocess

class TimeSegment:
    def __init__(self, start="00:00:00", end="00:00:00"):
        self.start = start
        self.end = end

class VideoFile:
    def __init__(self, path):
        self.path = path
        self.segments = [TimeSegment()]
        self.filename = os.path.basename(path)

class VideoSplitterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.videos = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Video Splitter')
        self.setGeometry(100, 100, 800, 600)

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建按钮
        select_btn = QPushButton('Select Videos', self)
        select_btn.clicked.connect(self.selectVideos)
        layout.addWidget(select_btn)

        # 压缩率设置
        compress_layout = QHBoxLayout()
        compress_label = QLabel('Compression Rate (CRF):', self)
        self.compress_rate = QSpinBox(self)
        self.compress_rate.setRange(0, 51)  # ffmpeg的CRF范围是0-51
        self.compress_rate.setValue(23)  # 默认值
        compress_layout.addWidget(compress_label)
        compress_layout.addWidget(self.compress_rate)
        compress_layout.addStretch()
        layout.addLayout(compress_layout)

        # 创建表格
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Video File', 'Start Time', 'End Time', 'Actions'])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # 开始处理按钮
        process_btn = QPushButton('Process Videos', self)
        process_btn.clicked.connect(self.processVideos)
        layout.addWidget(process_btn)

    def selectVideos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
        )
        
        if files:
            self.videos = [VideoFile(f) for f in files]
            self.updateTable()

    def updateTable(self):
        self.table.setRowCount(0)
        for video in self.videos:
            for i, segment in enumerate(video.segments):
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # 视频文件名
                if i == 0:
                    self.table.setItem(row, 0, QTableWidgetItem(video.filename))
                else:
                    self.table.setItem(row, 0, QTableWidgetItem(""))

                # 开始时间
                start_item = QTableWidgetItem(segment.start)
                self.table.setItem(row, 1, start_item)

                # 结束时间
                end_item = QTableWidgetItem(segment.end)
                self.table.setItem(row, 2, end_item)

                # 添加按钮
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                
                if i == len(video.segments) - 1:
                    add_btn = QPushButton("+")
                    current_video = video  # Create a reference to the current video
                    add_btn.clicked.connect(partial(self.addSegment, current_video))
                    btn_layout.addWidget(add_btn)
                
                if len(video.segments) > 1:
                    del_btn = QPushButton("-")
                    current_video = video  # Create a reference to the current video
                    current_segment = segment  # Create a reference to the current segment
                    del_btn.clicked.connect(partial(self.removeSegment, current_video, current_segment))
                    btn_layout.addWidget(del_btn)
                
                btn_layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, 3, btn_widget)

    def addSegment(self, video):
        video.segments.append(TimeSegment())
        self.updateTable()

    def removeSegment(self, video, segment):
        if segment in video.segments and len(video.segments) > 1:
            video.segments.remove(segment)
            self.updateTable()

    def validateTimeFormat(self, time_str):
        try:
            hours, minutes, seconds = map(int, time_str.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59:
                return True
        except:
            pass
        return False

    def processVideos(self):
        crf = self.compress_rate.value()
        
        # 收集所有分段信息
        for row in range(self.table.rowCount()):
            filename = self.table.item(row, 0).text()
            if filename:  # 新视频的第一行
                current_video = next((v for v in self.videos if v.filename == filename), None)
                if current_video:
                    segment_index = 0
            
            if current_video:
                start_time = self.table.item(row, 1).text()
                end_time = self.table.item(row, 2).text()
                
                if not self.validateTimeFormat(start_time) or not self.validateTimeFormat(end_time):
                    QMessageBox.warning(self, "Error", f"Invalid time format in {filename}")
                    return
                
                current_video.segments[segment_index].start = start_time
                current_video.segments[segment_index].end = end_time
                segment_index += 1

        # 处理每个视频
        for video in self.videos:
            input_path = video.path
            directory = os.path.dirname(input_path)
            filename = os.path.splitext(os.path.basename(input_path))[0]
            
            for i, segment in enumerate(video.segments):
                output_filename = f"{filename}_segment_{i+1}.mp4"
                output_path = os.path.join(directory, output_filename)
                
                try:
                    # 使用ffmpeg命令行进行视频分割
                    cmd = [
                        'ffmpeg', '-i', input_path,
                        '-ss', segment.start,
                        '-to', segment.end,
                        '-c:v', 'libx264',
                        '-crf', str(crf),
                        '-c:a', 'aac',
                        output_path,
                        '-y'  # 覆盖已存在的文件
                    ]
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        raise Exception(f"FFmpeg error: {stderr.decode()}")
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error processing {video.filename}: {str(e)}")
                    return

        QMessageBox.information(self, "Success", "All videos have been processed successfully!")

def main():
    app = QApplication(sys.argv)
    ex = VideoSplitterApp()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 