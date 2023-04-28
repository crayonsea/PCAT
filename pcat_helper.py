import numpy as np
import file_utils
import pptk


class AnnotateViewer(pptk.viewer):
    def __init__(self, port):
        self._portNumber = port
        self._process = None


class AnnotateViewerHelpler:
    def __init__(self, client_port, viewer_hwnd) -> None:
        self.port = client_port
        self.hwnd = viewer_hwnd
        self.viewer = AnnotateViewer(self.port)
        self._anno_mode = 'sem'
        self.init_default_params()

    def init_default_params(self):
        self.set_point_size_range([0.0001, 0.001, 0.005, 0.01, 0.02])
        self.setup(np.zeros(0), np.zeros(0))

    @property
    def cur_labels(self):
        if self._anno_mode == 'sem':
            return self.sem_labels
        else:
            return self.ins_labels
    
    def set_anno_mode(self, value):
        self._anno_mode = str(value)

    # init data

    def setup(self, points, colors):
        # data
        self.points = points
        self.colors = colors
        # label
        self.sem_labels = np.zeros(points.shape[0]).astype(np.int16)
        self.ins_labels = np.zeros(points.shape[0]).astype(np.int16)
        self._anno_mode = 'sem'
        # focus
        self.focus_stack = [np.arange(points.shape[0])]
        return

    def set_color_map(self, color_map=None, scale=None):
        self.color_map = color_map
        self.scale = scale
        self.viewer.color_map(color_map, scale)
    
    # pack data
    
    def get_labels_info(self):
        sem_label_points = np.bincount(self.sem_labels)
        sem_label_points = np.pad(sem_label_points, (0, len(self.color_map) - len(sem_label_points)), 'constant', constant_values=0)
        
        ins_label_counts = [''] * len(sem_label_points)
        for i in range(len(ins_label_counts)):
            cur_sem_ins = self.ins_labels[self.sem_labels == i]
            nonzero_cnt = len(np.unique(cur_sem_ins[cur_sem_ins != 0]))
            unanno_cnt = (cur_sem_ins == 0).sum()
            if len(cur_sem_ins) == 0:
                ins_label_counts[i] = ''
            else:
                ins_label_counts[i] = f'{nonzero_cnt} <{unanno_cnt}>'
        
        return sem_label_points, ins_label_counts
    
    # io
    
    def load_data(self, filepath):
        points, colors = file_utils.load_data(filepath)
        self.setup(points, colors)
        self.viewer.clear()
        self.viewer.reset()
        self.viewer.load(points, colors, self.cur_labels, color_map=self.color_map, scale=self.scale)
        return self.get_labels_info()
    
    def load_labels(self, filepath):
        labels = file_utils.load_label(filepath)
        print('labels load', labels.shape)
        sem_labels = labels[0]
        ins_labels = labels[1]
        if sem_labels.shape == self.sem_labels.shape and ins_labels.shape == self.ins_labels.shape:
            self.sem_labels = sem_labels
            self.ins_labels = ins_labels
            self.viewer.attributes(self.colors, self.cur_labels)
        else:
            print('点云与标签 shape 不一致')
        return self.get_labels_info()
    
    def save_labels(self, filepath):
        labels = np.vstack([self.sem_labels, self.ins_labels])
        file_utils.save_label(filepath, labels)
        print('labels saved:', labels.shape)
    
    # action
    
    def render(self, mask, label_type='sem'):
        mask = self.focus_stack[-1] if mask is None else mask
        points = self.points[mask]
        colors = self.colors[mask]
        cur_labels = self.cur_labels[mask]
        # p = get_perspective()
        self.viewer.clear()
        self.viewer.reset()
        self.viewer.load(points, colors, cur_labels, color_map=self.color_map, scale=self.scale)
        # set_perspective(p)
        return self.get_labels_info()
    
    def annotate(self, label: str, overwrite=True, atype='sem'):
        selected = self.viewer.get('selected')
        if len(selected) == 0:
            return

        mask = self.focus_stack[-1]
        
        if atype == 'sem':
            label = int(label)
        else:
            label = 0 if label is None else self.cur_labels.max() + 1
        
        if overwrite or int(label) == 0:
            self.cur_labels[mask[selected]] = int(label)
        else:
            cur_region_mask = mask[selected]
            cur_region_change_mask = np.where(self.cur_labels[cur_region_mask] == 0)
            self.cur_labels[cur_region_mask[cur_region_change_mask]] = int(label)
        
        attr_id = self.viewer.get('curr_attribute_id')
        self.viewer.attributes(self.colors[mask], self.cur_labels[mask])
        self.viewer.set(curr_attribute_id=attr_id[0], selected=[])
        return self.get_labels_info()
    
    # def annotate_ins(self, sem_label: str, overwrite=True):
    #     selected = self.viewer.get('selected')
    #     if len(selected) == 0:
    #         return
        
    #     mask = self.focus_stack[-1]
        
    #     if overwrite or int(label) == 0:
    #         self.sem_labels[mask[selected]] = int(label)
    #     else:
    #         print('here')
    #         cur_region_mask = mask[selected]
    #         cur_region_change_mask = np.where(self.sem_labels[cur_region_mask] == 0)
    #         self.sem_labels[cur_region_mask[cur_region_change_mask]] = int(label)
        
    #     attr_id = self.viewer.get('curr_attribute_id')
    #     self.viewer.attributes(self.colors[mask], self.sem_labels[mask])
    #     self.viewer.set(curr_attribute_id=attr_id[0], selected=[])
    #     pass
    
    def focus(self, ftype):
        # select
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
        # sem label
        elif ftype is None:
            self.focus_stack = self.focus_stack[:1]
        else:
            filter_id = int(ftype)
            selected = self.sem_labels == filter_id
            self.focus_stack = self.focus_stack[:1]
            self.focus_stack.append(self.focus_stack[-1][selected])
        
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
