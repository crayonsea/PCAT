import os
import sys
import win32api
import win32gui
import win32con

from PyQt5.QtCore import QProcess, QThreadPool
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog

import socket
from labels import labels_dict_pack
from worker import Worker

# !note: import pptk on the last
from pcat_helper import AnnotateViewerHelpler
from pptk.viewer.viewer import _viewer_dir


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        self.setCentralWidget(widget)
        self.layout = layout
        
        # siderbar
        sidebar_layout = self.create_sidebar_layout(labels_dict_pack)
        self.layout.addLayout(sidebar_layout, 1)
        
        # viewer container
        self.startViewerProcess()
        
        # process busy task
        self.threadpool = QThreadPool()

    # close event

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(self, 'Message', "是否退出？", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.closeProcess()
            event.accept()
        else:
            event.ignore()

    # Process
    
    def startViewerProcess(self):
        # socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        s.listen(0)
        # process
        self._viewer_process = QProcess()
        self._viewer_process.readyRead.connect(self.bindViewerProcessContainer)
        self._viewer_process.start(os.path.join(_viewer_dir, 'viewer'), [str(s.getsockname()[1])])
        # client port
        self._viewer_port = s.accept()[-1][-1]

    def bindViewerProcessContainer(self):
        hwnd = win32gui.FindWindowEx(0, 0, None, "viewer")
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        window = QtGui.QWindow.fromWinId(hwnd)
        windowContainer = QtWidgets.QWidget.createWindowContainer(window)
        self._viewer_hwnd = hwnd
        self._viewer_windowContainer = windowContainer
        self.layout.addWidget(self._viewer_windowContainer, 9)
        # manage viewer
        self.viewer = AnnotateViewerHelpler(self._viewer_port, self._viewer_hwnd)
        self.viewer.set_color_map(labels_dict_pack['color_rgb'], [0, len(labels_dict_pack['color_rgb']) - 1])
    
    def closeProcess(self, kill=True):
        if self._viewer_process:
            if kill:
                self._viewer_process.kill()
            else:
                self._viewer_process.terminate()

    # layout

    def create_sidebar_layout(self, labels_dict_pack):
        sidebar_layout = QVBoxLayout()

        # file
        hlayout = QHBoxLayout()
        btn_load = QPushButton('打开点云')
        btn_load.setFocus()
        btn_save = QPushButton('导出标注')
        btn_load.clicked.connect(self.on_click_load_file)
        btn_save.clicked.connect(self.on_click_save_label)
        hlayout.addWidget(btn_load)
        hlayout.addWidget(btn_save)
        sidebar_layout.addLayout(hlayout)

        sidebar_layout.addSpacing(20)

        btn_load_label = QPushButton('加载标注')
        btn_load_label.clicked.connect(self.on_click_load_label)
        sidebar_layout.addWidget(btn_load_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(line)
        sidebar_layout.addSpacing(20)

        # label
        for label_id, label, color in zip(labels_dict_pack['label_id'], labels_dict_pack['label_cn'], labels_dict_pack['color_hex']):
            hlayout = QHBoxLayout()
            qlabel = QLabel(label)
            button = QPushButton(label)
            button.setObjectName(str(label_id))
            button.setStyleSheet(f"background-color: {QtGui.QColor(color).name()}")
            button.clicked.connect(self.on_click_set_sem_label)
            hlayout.addWidget(qlabel)
            hlayout.addWidget(button)
            sidebar_layout.addLayout(hlayout)    
        
        sidebar_layout.addStretch(1)
        
        # focus
        hlayout = QHBoxLayout()
        btn_focus_in = QPushButton('前进')
        btn_focus_in.setObjectName('forward')
        btn_focus_out = QPushButton('回退')
        btn_focus_out.setObjectName('backward')
        btn_focus_in.clicked.connect(self.on_click_focus)
        btn_focus_out.clicked.connect(self.on_click_focus)
        hlayout.addWidget(btn_focus_in)
        hlayout.addWidget(btn_focus_out)
        sidebar_layout.addLayout(hlayout)
        sidebar_layout.addStretch(1)
        
        return sidebar_layout
    
    # key event
    
    def keyPressEvent(self, event):
        print(event)
        print(event.text())
        # view
        if event.text() == 'q':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0x31, 0)
        elif event.text() == 'w':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0x33, 0)
        elif event.text() == 'e':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0x37, 0)
        elif event.text() == 'r':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0x35, 0)
        # attrs
        elif event.text() == '[':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0xDB, 0)
        elif event.text() == ']':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0xDD, 0)
        # todo
        elif event.text() == ',' or event.text() == '<':
            pass
        elif event.text() == '.' or event.text() == '>':
            pass
        else:
            pass
        return
    
    def keyReleaseEvent(self, event):
        if event.text() == '~':
            pass
        # point size
        elif event.text() == '-' or event.text() == '_':
            self.viewer.decrease_point_size()
        elif event.text() == '=' or event.text() == '+':
            self.viewer.increase_point_size()
        return
    
    # click event
    
    def on_click_load_file(self):
        file_dialog = QFileDialog()
        filepath, _ = file_dialog.getOpenFileName(None, '选择文件')
        _, extension = os.path.splitext(filepath)
        if extension in ['.bin']:
            worker = Worker(self.viewer.load_data, filepath)
            self.threadpool.start(worker)
            self.cur_filename = os.path.basename(filepath)

    def on_click_load_label(self):
        file_dialog = QFileDialog()
        filepath, _ = file_dialog.getOpenFileName(None, '选择文件')
        _, extension = os.path.splitext(filepath)
        if extension in ['.bin']:
            worker = Worker(self.viewer.load_labels, filepath)
            self.threadpool.start(worker)

    def on_click_save_label(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        filepath, _ = QFileDialog.getSaveFileName(None, "导出文件", f'{self.cur_filename[:-4]}_labels.bin', "二进制文件 (*.bin)", options=options)
        _, extension = os.path.splitext(filepath)
        if extension in ['.bin']:
            worker = Worker(self.viewer.save_labels, filepath)
            self.threadpool.start(worker)
    
    def on_click_set_sem_label(self):
        worker = Worker(self.viewer.annotate, self.sender().objectName())
        self.threadpool.start(worker)
    
    def on_click_focus(self):
        worker = Worker(self.viewer.focus, self.sender().objectName())
        self.threadpool.start(worker)


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("fusion")

    try:
        win = MainWindow()
        win.setWindowTitle('PC Anno Tool')
        win.setMinimumSize(800, 600)
        win.showMaximized()
        win.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("Exception occurred: {}".format(str(e)))
    finally:
        win.closeProcess()
