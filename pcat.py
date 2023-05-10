import os
import sys
import win32api
import win32gui
import win32con

from PyQt5.QtCore import QProcess, QThreadPool
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog, QShortcut

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
        self.widget = widget
        self.layout = layout

        # state
        self.overwriteMode = True
        self.overwriteModeText = { True: '标注覆盖已开启', False: '标注覆盖已关闭' }
        self.overwriteModeColor = { True: '#90EE90;', False: '#FFC0CB;' }

        self.ins_AnnoMode = False
        self.ins_AnnoModeText = { True: '实例标注已开启', False: '实例标注已关闭' }
        self.ins_AnnoModeColor = { True: '#90EE90;', False: '#FFC0CB;' }

        # data
        self.sem_anno_btn = []
        self.ins_anno_btn = []
        
        # layout
        # - siderbar
        self.sidebar_layout_sem = self.create_sidebar_layout_sem()
        # - siderbar
        self.sidebar_layout_ins = self.create_sidebar_layout_ins()
        
        # viewer container
        self.startViewerProcess()
        
        # process busy task
        self.threadpool = QThreadPool()
    
    # data model
    def update_data_model(self, info):
        if info is None:
            return
        counts = info[self.ins_AnnoMode]
        for cnt, btn in zip(counts, self.ins_anno_btn):
            btn : QPushButton
            btn.setText(str(cnt))

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
        self._viewer_process.readyReadStandardOutput.connect(self.bindViewerProcessContainer)
        res1 = s.getsockname()
        self._viewer_process.start(os.path.join(_viewer_dir, 'viewer'), [str(res1[1])])
        # self._viewer_port = s.accept()[-1][-1]
        res2 = s.accept()
        print('client port:', res2[-1][-1])
        # self._viewer_port = res2[-1][-1]

    def bindViewerProcessContainer(self):
        # pptk viewer port
        import struct
        data = self._viewer_process.readAllStandardOutput().data()
        port = struct.unpack('H', data)
        self._viewer_port = int(port[0])
        print('viewer port:', self._viewer_port)
        # pptk viewer hwnd
        hwnd = win32gui.FindWindowEx(0, 0, None, "viewer")
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        window = QtGui.QWindow.fromWinId(hwnd)
        windowContainer = QtWidgets.QWidget.createWindowContainer(window)
        self._viewer_hwnd = hwnd
        self._viewer_windowContainer = windowContainer
        self.layout.addLayout(self.sidebar_layout_sem, 1)
        self.layout.addWidget(self._viewer_windowContainer, 8)
        self.layout.addLayout(self.sidebar_layout_ins, 1)
        self.widget.setFocus()
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

    def create_anno_label_layout(self, clicked_func, anno_type='sem'):
        # label
        vlayout = QVBoxLayout()
        if anno_type == 'sem':
            for label_id, label, color in zip(labels_dict_pack['label_id'], labels_dict_pack['label_cn'], labels_dict_pack['color_hex']):
                hlayout = QHBoxLayout()
                qlabel = QLabel(label)
                button = QPushButton(label)
                button.setObjectName(str(label_id))
                button.setStyleSheet(f"background-color: {QtGui.QColor(color).name()}")
                button.clicked.connect(clicked_func)
                self.sem_anno_btn.append(button)
                hlayout.addWidget(qlabel)
                hlayout.addWidget(button)
                vlayout.addLayout(hlayout)
        elif anno_type == 'ins':
            for label_id, label, color in zip(labels_dict_pack['label_id'], labels_dict_pack['label_cn'], labels_dict_pack['color_hex']):
                hlayout = QHBoxLayout()
                qlabel = QLabel(label)
                button = QPushButton(str(0))
                button.setCheckable(True)
                button.setChecked(True)
                button.setObjectName(str(label_id))
                button.clicked.connect(clicked_func)
                self.ins_anno_btn.append(button)
                hlayout.addWidget(qlabel)
                hlayout.addWidget(button)
                vlayout.addLayout(hlayout)
            pass
        else:
            raise Exception('anno_type error')
        return vlayout

    def create_sidebar_layout_sem(self):
        sidebar_layout = QVBoxLayout()
        
        # file
        hlayout = QHBoxLayout()
        btn_load = QPushButton('打开点云')
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
        sidebar_layout.addSpacing(20)
        
        # overwirte
        
        btn_overwirte = QPushButton(self.overwriteModeText[self.overwriteMode])
        btn_overwirte.setStyleSheet(f"background-color: {self.overwriteModeColor[self.overwriteMode]}")
        btn_overwirte.clicked.connect(self.on_click_toggle_overwrite)
        btn_overwirte_shortcut = QShortcut('z', self)
        btn_overwirte_shortcut.activated.connect(btn_overwirte.click)
        sidebar_layout.addWidget(btn_overwirte)
        sidebar_layout.addSpacing(20)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(line)
        sidebar_layout.addSpacing(20)

        # label
        sem_label_layout = self.create_anno_label_layout(self.on_click_set_sem_label, anno_type='sem')
        sidebar_layout.addLayout(sem_label_layout)
        sidebar_layout.addStretch(1)
        
        return sidebar_layout
    
    def create_sidebar_layout_ins(self):
        
        sidebar_layout = QVBoxLayout()
        
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
        sidebar_layout.addSpacing(20)

        hlayout = QHBoxLayout()
        btn_add_ins_label = QPushButton('添加实例')
        btn_add_ins_label.setObjectName('add')
        btn_add_ins_label.clicked.connect(self.on_click_set_ins_label)
        hlayout.addWidget(btn_add_ins_label)
        btn_del_ins_label = QPushButton('删除实例')
        btn_del_ins_label.setObjectName('del')
        btn_del_ins_label.clicked.connect(self.on_click_set_ins_label)
        hlayout.addWidget(btn_del_ins_label)
        sidebar_layout.addLayout(hlayout)
        sidebar_layout.addSpacing(20)
        
        btn_ins_anno = QPushButton(self.ins_AnnoModeText[self.ins_AnnoMode])
        btn_ins_anno.setStyleSheet(f"background-color: {self.ins_AnnoModeColor[self.ins_AnnoMode]}")
        btn_ins_anno.clicked.connect(self.on_click_toggle_ins_anno)
        sidebar_layout.addWidget(btn_ins_anno)
        sidebar_layout.addSpacing(20)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(line)
        sidebar_layout.addSpacing(20)

        # cb_sem_group = QComboBox()
        # for label_id, label, color in zip(labels_dict_pack['label_id'], labels_dict_pack['label_cn'], labels_dict_pack['color_hex']):
        #     cb_sem_group.addItem(label, label_id)
        # self.cb_sem_group = cb_sem_group
        ins_label_layout = self.create_anno_label_layout(self.on_click_set_sem_filter_label, anno_type='ins')
        sidebar_layout.addLayout(ins_label_layout)
        sidebar_layout.addStretch(1)
        
        return sidebar_layout
    
    # mouse event
    def wheelEvent(self,event):
        sroll=event.angleDelta()
        if(sroll.y()>0):
            win32api.SendMessage(
                self.viewer.hwnd, win32con.WM_MOUSEWHEEL, 120 << 16, 0)
        else :
            win32api.SendMessage(self.viewer.hwnd,win32con.WM_MOUSEWHEEL,-120<<16,0)
        return 

    # key event
    
    def keyPressEvent(self, event):
        # print(event.text(), event)
        print(event.text())
        # view
        if event.text() == 'q':
            worker = Worker(self.viewer.set_camera, 'top')
            self.threadpool.start(worker)
        elif event.text() == 'w':
            worker = Worker(self.viewer.set_camera, 'front')
            self.threadpool.start(worker)
        elif event.text() == 'e':
            worker = Worker(self.viewer.set_camera, 'bottom')
            self.threadpool.start(worker)
        elif event.text() == 'a':
            worker = Worker(self.viewer.set_camera, 'left')
            self.threadpool.start(worker)
        elif event.text() == 's':
            worker = Worker(self.viewer.set_camera, 'back')
            self.threadpool.start(worker)
        elif event.text() == 'd':
            worker = Worker(self.viewer.set_camera, 'right')
            self.threadpool.start(worker)
        elif event.text() == 'r':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0x35, 0)
        elif event.text() == 'c':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0x43, 0)
        # attrs
        elif event.text() == '[':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0xDB, 0)
        elif event.text() == ']':
            win32api.SendMessage(self.viewer.hwnd, win32con.WM_KEYDOWN, 0xDD, 0)
        # todo
        elif event.text() == ',' or event.text() == '<':
            win32api.SendMessage(
                self.viewer.hwnd, win32con.WM_MOUSEWHEEL, -120 << 16, 0)
        elif event.text() == '.' or event.text() == '>':
            win32api.SendMessage(
                self.viewer.hwnd, win32con.WM_MOUSEWHEEL, 120 << 16, 0)
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
            worker.signals.result.connect(self.update_data_model)
            self.threadpool.start(worker)
            self.cur_filename = os.path.basename(filepath)

    def on_click_load_label(self):
        file_dialog = QFileDialog()
        filepath, _ = file_dialog.getOpenFileName(None, '选择文件')
        _, extension = os.path.splitext(filepath)
        if extension in ['.bin']:
            worker = Worker(self.viewer.load_labels, filepath)
            worker.signals.result.connect(self.update_data_model)
            self.threadpool.start(worker)

    def on_click_save_label(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        filepath, _ = QFileDialog.getSaveFileName(None, "导出文件", f'{self.cur_filename[:-4]}_labels.bin', "二进制文件 (*.bin)", options=options)
        _, extension = os.path.splitext(filepath)
        if extension in ['.bin']:
            worker = Worker(self.viewer.save_labels, filepath)
            self.threadpool.start(worker)

    def on_click_toggle_overwrite(self):
        btn = self.sender()
        btn: QPushButton
        self.overwriteMode = not self.overwriteMode
        btn.setText(self.overwriteModeText[self.overwriteMode])
        btn.setStyleSheet(f"background-color: {self.overwriteModeColor[self.overwriteMode]}")

    def on_click_toggle_ins_anno(self):
        btn = self.sender()
        btn: QPushButton
        self.ins_AnnoMode = not self.ins_AnnoMode
        btn.setText(self.ins_AnnoModeText[self.ins_AnnoMode])
        btn.setStyleSheet(f"background-color: {self.ins_AnnoModeColor[self.ins_AnnoMode]}")
        for btn in self.sem_anno_btn:
            btn.setEnabled(not self.ins_AnnoMode)
        for btn in self.ins_anno_btn:
            btn.setChecked(True)
        self.viewer.set_anno_mode({True: 'ins', False: 'sem'}[self.ins_AnnoMode])
        worker = Worker(self.viewer.render, None)
        worker.signals.result.connect(self.update_data_model)
        self.threadpool.start(worker)

    def on_click_set_sem_label(self):
        worker = Worker(self.viewer.annotate, self.sender().objectName(), overwrite=self.overwriteMode)
        worker.signals.result.connect(self.update_data_model)
        self.threadpool.start(worker)

    def on_click_set_ins_label(self):
        sem_id = [btn.objectName() for btn in self.ins_anno_btn if not btn.isChecked()]
        if len(sem_id) == 0:
            return
        sem_id = sem_id[0]
        if self.sender().objectName() == 'del':
            sem_id = None
        print(self.viewer.get_labels_info())
        worker = Worker(self.viewer.annotate, sem_id, overwrite=self.overwriteMode, atype='ins')
        worker.signals.result.connect(self.update_data_model)
        self.threadpool.start(worker)

    def on_click_set_sem_filter_label(self):
        # only one checked
        cur_btn = self.sender()
        cur_btn : QPushButton
        for btn in self.ins_anno_btn:
            if btn is not self.sender():
                btn : QPushButton
                btn.setChecked(True)
        
        if cur_btn.isChecked():
            filter_id = None
        else:
            filter_id = cur_btn.objectName()
        # focus by sem id
        worker = Worker(self.viewer.focus, filter_id)
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
        sys.exit(app.exec_())
    except Exception as e:
        print("Exception occurred: {}".format(str(e)))
    finally:
        win.closeProcess()
