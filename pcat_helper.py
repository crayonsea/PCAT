import numpy as np
import file_utils
import pptk


class AnnotateViewer(pptk.viewer):
    def __init__(self, port):
        self._portNumber = port - 1
        self._process = None


class AnnotateViewerHelpler:
    def __init__(self, client_port, viewer_hwnd) -> None:
        self.port = client_port
        self.hwnd = viewer_hwnd
        self.viewer = AnnotateViewer(self.port)
        self.init_default_params()
    
    def init_default_params(self):
        self.set_point_size_range([0.0001, 0.001, 0.005, 0.01, 0.02])
    
    def set_color_map(self, color_map=None, scale=None):
        self.color_map = color_map
        self.scale = scale
        self.viewer.color_map(color_map, scale)

    # init data
    
    def setup(self, points, colors):
        # data
        self.points = points
        self.colors = colors
        # label
        self.sem_labels = np.zeros(points.shape[0])
        self.ins_labels = np.zeros(points.shape[0])
        # focus
        self.focus_stack = [np.arange(points.shape[0])]
        return
    
    # io
    
    def load_data(self, filepath):
        points, colors = file_utils.load_data(filepath)
        self.setup(points, colors)
        self.viewer.clear()
        self.viewer.reset()
        self.viewer.load(points, colors, self.sem_labels, color_map=self.color_map, scale=self.scale)
    
    def load_labels(self, filepath):
        labels = file_utils.load_label(filepath)
        print('labels load', labels.shape)
        sem_labels = labels[0]
        ins_labels = labels[1]
        if sem_labels.shape == self.sem_labels.shape and ins_labels == self.ins_labels:
            self.sem_labels = sem_labels
            self.ins_labels = ins_labels
            self.viewer.attributes(self.colors, self.sem_labels)
        else:
            print('点云与标签 shape 不一致')
    
    def save_labels(self, filepath):
        labels = np.vstack([self.sem_labels, self.ins_labels])
        file_utils.save_label(filepath, labels)
        print('labels saved:', labels.shape)
    
    # action
    
    def render(self, mask):
        points = self.points[mask]
        colors = self.colors[mask]
        sem_labels = self.sem_labels[mask]
        # p = get_perspective()
        self.viewer.clear()
        self.viewer.reset()
        self.viewer.load(points, colors, sem_labels, color_map=self.color_map, scale=self.scale)
        # set_perspective(p)
        return
    
    def annotate(self, label: str):
        
        selected = self.viewer.get('selected')
        if len(selected) == 0:
            return

        mask = self.focus_stack[-1]
        self.sem_labels[mask[selected]] = int(label)
        attr_id = self.viewer.get('curr_attribute_id')
        self.viewer.attributes(self.colors[mask], self.sem_labels[mask])
        self.viewer.set(curr_attribute_id=attr_id[0], selected=[])
        return
    
    def focus(self, ftype):  
        if ftype == 'forward':
            selected = self.viewer.get('selected')
            if len(selected) != 0:
                self.focus_stack.append(self.focus_stack[-1][selected])
            else:
                return
        elif ftype == 'backward':
            if len(self.focus_stack) > 1:
                self.focus_stack.pop()
            else:
                return
        
        cur_focus_mask = self.focus_stack[-1]
        self.render(cur_focus_mask)
    
    # point size

    def set_point_size_range(self, point_size_range_list):
        self._point_size_idx = 0
        self._point_size_range = list(sorted(point_size_range_list))        
    
    def increase_point_size(self):
        if self._point_size_idx < len(self._point_size_range) - 1:
            self._point_size_idx += 1
            self.viewer.set(point_size=self._point_size_range[self._point_size_idx])
    
    def decrease_point_size(self):
        if self._point_size_idx > 0:
            self._point_size_idx -= 1
            self.viewer.set(point_size=self._point_size_range[self._point_size_idx])
